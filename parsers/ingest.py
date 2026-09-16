import os
import sys
import re
import argparse
import hashlib
import json
import requests
import io
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

# Import standard google API client libraries if available
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    GOOGLE_DRIVE_SDK_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_SDK_AVAILABLE = False

# Import text extraction logic from existing parse_pdf.py and parse_mercadopago_csv.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    import parse_pdf
except ImportError:
    parse_pdf = None

try:
    import parse_mercadopago_csv
except ImportError:
    parse_mercadopago_csv = None

try:
    import parse_schwab_csv
except ImportError:
    parse_schwab_csv = None

try:
    import parse_iol
except ImportError:
    parse_iol = None

# Paths setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
NORMALIZED_DIR = os.path.join(DATA_DIR, "normalized")
INGESTED_REGISTRY_PATH = os.path.join(NORMALIZED_DIR, "ingested_files.csv")
TEMP_RAW_DIR = os.path.join(DATA_DIR, "raw", "temp")

# Load environment variables
load_dotenv(dotenv_path=os.path.join(REPO_ROOT, ".env"))

def get_drive_service(credentials_path):
    """Authenticates and returns the Google Drive API service."""
    if not GOOGLE_DRIVE_SDK_AVAILABLE:
        raise ImportError(
            "❌ Google API client SDK is not installed or import failed. "
            "Please check requirements.txt."
        )
    
    # If not found in current directory and path is relative, resolve against REPO_ROOT
    if not os.path.isabs(credentials_path) and not os.path.exists(credentials_path):
        fallback_path = os.path.join(REPO_ROOT, credentials_path)
        if os.path.exists(fallback_path):
            credentials_path = fallback_path

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"❌ Service account credentials file not found at: {credentials_path}. "
            f"Please verify DRIVE_CREDENTIALS_FILE in your .env."
        )
        
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=scopes
    )
    return build('drive', 'v3', credentials=creds)

def calculate_sha256(file_bytes):
    """Calculates SHA-256 hash of file content bytes."""
    sha256 = hashlib.sha256()
    sha256.update(file_bytes)
    return sha256.hexdigest()

def is_already_ingested(file_hash):
    """Checks if the file hash has already been successfully ingested."""
    if not os.path.exists(INGESTED_REGISTRY_PATH):
        return False
    try:
        df = pd.read_csv(INGESTED_REGISTRY_PATH)
        success_mask = (df["file_hash"] == file_hash) & (df["status"] == "success")
        return success_mask.any()
    except Exception as e:
        print(f"⚠️ Warning reading ingested registry: {e}. Defaulting to False.")
        return False

def register_ingestion(file_name, file_hash, status, account_id, notes=""):
    """Registers file ingestion metadata in ingested_files.csv."""
    os.makedirs(NORMALIZED_DIR, exist_ok=True)
    headers = ["file_name", "file_hash", "ingested_at", "status", "account_id", "notes"]
    
    new_row = {
        "file_name": file_name,
        "file_hash": file_hash,
        "ingested_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "account_id": account_id if account_id else "-",
        "notes": notes
    }
    
    if os.path.exists(INGESTED_REGISTRY_PATH):
        try:
            df = pd.read_csv(INGESTED_REGISTRY_PATH)
            # Remove existing record of the same hash if it exists (e.g. updating failed/review status)
            df = df[df["file_hash"] != file_hash]
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        except Exception:
            df = pd.DataFrame([new_row])
    else:
        df = pd.DataFrame([new_row])
        
    df.to_csv(INGESTED_REGISTRY_PATH, index=False)

def parse_filename(filename):
    """
    Parses name of format YYYY-MM_institution_type_desc.ext or native broker exports.
    Returns (period, institution, account_id, file_ext)
    """
    base_name = os.path.basename(filename)
    name_without_ext, ext = os.path.splitext(base_name)
    ext = ext.lower().replace(".", "")
    
    # Native Schwab Positions pattern: Individual-Positions-YYYY-MM-DD...
    pos_match = re.search(r"Individual[-_]Positions[-_](\d{4})[-_](\d{2})", name_without_ext, re.IGNORECASE)
    if pos_match:
        period = f"{pos_match.group(1)}-{pos_match.group(2)}"
        return period, "schwab", "schwab_broker", ext

    # Native Schwab Transactions pattern: Individual_..._Transactions_YYYYMMDD...
    txn_match = re.search(r"Transactions.*?(\d{4})(\d{2})\d{2}", name_without_ext, re.IGNORECASE)
    if txn_match:
        period = f"{txn_match.group(1)}-{txn_match.group(2)}"
        return period, "schwab", "schwab_broker", ext

    # Native IOL patterns
    name_clean = name_without_ext.lower().replace(" ", "").replace("_", "")
    if "operacionesfinalizadas" in name_clean:
        return "2026-09", "iol", "iol_broker", ext
    if "movimientoshistoricos" in name_clean:
        return "2026-09", "iol", "iol_broker", ext
    if "resumencuenta" in name_clean:
        return "2026-09", "iol", "iol_broker", ext

    parts = name_without_ext.split("_")
    if len(parts) < 3:
        # Fallback or invalid format
        return None, None, None, ext
        
    period = parts[0]       # YYYY-MM
    institution = parts[1].lower()  # galicia, schwab, etc.
    file_type = parts[2].lower()    # statement, movements, positions, etc.
    
    # Derivar account_id context
    if institution in ["schwab", "iol"]:
        account_id = f"{institution}_broker"
    else:
        account_id = f"{institution}_{file_type}"
        if len(parts) > 3:
            # Si tiene descripción como _ars o _usd
            desc = parts[3].lower()
            if desc in ["ars", "usd"]:
                account_id = f"{institution}_{desc}"
            
    return period, institution, account_id, ext

def call_gemini_api(prompt_text, api_key):
    """Calls Gemini API directly using REST to extract structured JSON data."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=45)
    response.raise_for_status()
    result = response.json()
    
    try:
        extracted_text = result['candidates'][0]['content']['parts'][0]['text']
        return extracted_text.strip()
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected response structure from Gemini API: {result}")

def process_pdf_file(temp_file_path, file_name, account_id, gemini_api_key, dry_run=False):
    """Processes PDF file using LLM extraction and parse_pdf normalization."""
    if not parse_pdf:
        return False, "parse_pdf module import failed."
        
    print(f"📄 Extracting text from PDF locally...")
    pdf_text = parse_pdf.extract_pdf_text(temp_file_path)
    print(f"📖 Extracted {len(pdf_text)} characters.")
    
    # Generate prompt system text
    prompt_buffer = io.StringIO()
    # Save stdout to capture prompt generation
    original_stdout = sys.stdout
    sys.stdout = prompt_buffer
    try:
        # Generate prompt using parse_pdf internal utility
        parse_pdf.generate_prompt_request(pdf_text, account_id, "dummy_output_path")
    finally:
        sys.stdout = original_stdout
    
    prompt_content = prompt_buffer.getvalue()
    # Note: parse_pdf's generate_prompt_request prints a couple of confirmation lines,
    # but the prompt itself was written to "dummy_output_path". Let's write to a local string instead.
    
    # Re-generate clean prompt request content to avoid writing prompt files
    # We do a simplified version of generate_prompt_request logic to obtain the prompt string directly.
    system_prompt = f"""You are a financial data extraction assistant.
Your task is to extract all transactions and closing balances from the bank/broker statement text provided below.

### Output Format:
You must output a single valid JSON object containing two lists:
1. "balances": A list of closing balance snapshots.
2. "transactions": A list of transaction records.

Do NOT include any markdown code formatting (like ```json), explanations, or text outside the JSON. Return only the raw JSON.

### JSON Schema:
{{
  "balances": [
    {{
      "as_of_date": "YYYY-MM-DD",
      "account_id": "{account_id}",
      "currency": "ARS" | "USD",
      "balance_original": 1234.56,
      "liquidity_tier": "immediate" | "short_term" | "invested",
      "notes": "Statement closing balance"
    }}
  ],
  "transactions": [
    {{
      "txn_date": "YYYY-MM-DD",
      "posted_date": "YYYY-MM-DD",
      "description_raw": "Original bank transaction description",
      "amount_original": 123.45,
      "currency": "ARS" | "USD",
      "direction": "inflow" | "outflow",
      "normalized_type": "expense" | "income" | "internal_transfer" | "investment_funding" | "asset_purchase" | "asset_sale" | "fee" | "fx_conversion" | "card_payment" | "unknown",
      "counterparty": "Merchant or recipient name",
      "is_internal_transfer": true | false,
      "expense_bucket": "housing" | "food" | "transport" | "health" | "social" | "shopping" | "hobbies" | "other" | "-",
      "expense_type": "fixed" | "discretionary" | "-",
      "notes": "Transaction details"
    }}
  ]
}}

### Account ID Context:
The statement belongs to account: {account_id}

### Rules:
1. "balance_original" and "amount_original" must be numeric floats.
2. Positive transaction amounts denote inflows, negative denote outflows.
3. If an expense_bucket or expense_type is not applicable, use "-".
4. Determine the expense_type (fixed vs. discretionary) based on the criteria:
   - "fixed": Housing/rent, health insurance, essential food/groceries, basic utilities/services.
   - "discretionary": Ocio/dining out, hobbies, shopping, social events, optional subscriptions.
   - "-": If the transaction is not an expense.
5. If posted_date is not available, default to txn_date.

### Input Text:
----------------------------------------
{pdf_text}
----------------------------------------
"""

    if not gemini_api_key:
        # Prompt generation mode only (no API key configured)
        prompt_output_path = os.path.join(os.path.dirname(temp_file_path), f"prompt_{os.path.splitext(file_name)[0]}.txt")
        with open(prompt_output_path, "w", encoding="utf-8") as f:
            f.write(system_prompt)
        return False, f"Missing GEMINI_API_KEY. Prompt request generated at: {prompt_output_path}"
        
    print(f"🤖 Sending data to Gemini API for extraction...")
    try:
        json_response = call_gemini_api(system_prompt, gemini_api_key)
    except Exception as e:
        return False, f"Gemini API request failed: {e}"
        
    # Write JSON response to temporary file
    temp_json_path = os.path.join(os.path.dirname(temp_file_path), f"response_{os.path.splitext(file_name)[0]}.json")
    with open(temp_json_path, "w", encoding="utf-8") as f:
        f.write(json_response)
        
    if dry_run:
        print(f"🔍 [Dry-Run] Extracted JSON Response preview:")
        try:
            parsed_json = json.loads(json_response)
            print(json.dumps(parsed_json, indent=2))
        except Exception:
            print(json_response)
        # Cleanup
        if os.path.exists(temp_json_path):
            os.remove(temp_json_path)
        return True, "Dry-Run verification successful. No changes written."
        
    print(f"📊 Normalizing extracted records...")
    try:
        parse_pdf.normalize_response(temp_json_path, file_name)
        # Cleanup
        if os.path.exists(temp_json_path):
            os.remove(temp_json_path)
        return True, "Successfully extracted and normalized."
    except Exception as e:
        # Keep response JSON for debug in case normalization failed
        return False, f"Normalization failed: {e}. JSON response kept at {temp_json_path}"

def process_csv_file(temp_file_path, file_name, institution, account_id, dry_run=False):
    """Processes tabular native CSV file using deterministic local rules."""
    if institution == "mercadopago":
        if not parse_mercadopago_csv:
            return False, "parse_mercadopago_csv module import failed."
        print(f"📝 Parsing Mercado Pago CSV deterministically: {file_name}")
        try:
            success, msg = parse_mercadopago_csv.parse_and_normalize(temp_file_path, file_name, dry_run)
            return success, msg
        except Exception as e:
            return False, f"Mercado Pago parser error: {e}"
    elif institution == "schwab":
        if not parse_schwab_csv:
            return False, "parse_schwab_csv module import failed."
        print(f"📈 Parsing Charles Schwab CSV deterministically: {file_name}")
        try:
            fn_lower = file_name.lower()
            if "position" in fn_lower:
                return parse_schwab_csv.parse_positions(temp_file_path, file_name, dry_run)
            elif "transaction" in fn_lower:
                return parse_schwab_csv.parse_transactions(temp_file_path, file_name, dry_run)
            else:
                with open(temp_file_path, "r", encoding="utf-8") as f:
                    snippet = f.read(500)
                if "Symbol" in snippet and "Mkt Val" in snippet:
                    return parse_schwab_csv.parse_positions(temp_file_path, file_name, dry_run)
                elif "Action" in snippet and "Fees & Comm" in snippet:
                    return parse_schwab_csv.parse_transactions(temp_file_path, file_name, dry_run)
                else:
                    return False, f"Unknown Schwab CSV format for file: {file_name}"
        except Exception as e:
            return False, f"Schwab parser error: {e}"
    elif institution == "iol":
        if not parse_iol:
            return False, "parse_iol module import failed."
        print(f"📈 Parsing Invertir Online (IOL) file deterministically: {file_name}")
        try:
            fn_lower = file_name.lower()
            if "operaciones" in fn_lower or "trade" in fn_lower:
                return parse_iol.parse_iol_operations(temp_file_path, file_name, dry_run)
            elif "movimientos" in fn_lower or "movement" in fn_lower:
                return parse_iol.parse_iol_movements(temp_file_path, file_name, dry_run)
            else:
                return False, f"Unknown IOL tabular file format for: {file_name}"
        except Exception as e:
            return False, f"IOL parser error: {e}"
    else:
        return False, f"No local deterministic CSV parser defined for institution: '{institution}'"

def process_file_content(temp_file_path, file_name, dry_run=False, gemini_api_key=None):
    """Routes the temp file to the correct parser based on extension and name."""
    period, institution, account_id, ext = parse_filename(file_name)
    
    if not period or not institution:
        return False, None, "Invalid filename structure. Must be YYYY-MM_institution_type.ext"
        
    print(f"🏷️ Identified File: Period={period}, Institution={institution}, Account={account_id}, Format={ext}")
    
    if ext == "pdf":
        if institution == "iol" and parse_iol:
            success, msg = parse_iol.parse_iol_statement_pdf(temp_file_path, file_name, dry_run)
        else:
            success, msg = process_pdf_file(temp_file_path, file_name, account_id, gemini_api_key, dry_run)
    elif ext in ["csv", "xlsx", "xls"]:
        success, msg = process_csv_file(temp_file_path, file_name, institution, account_id, dry_run)
    else:
        success, msg = False, f"Unsupported file format: '.{ext}'"
        
    return success, account_id, msg

def download_file_from_drive(service, file_id, dest_path):
    """Downloads a file from Google Drive to the local destination path."""
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        
    fh.seek(0)
    with open(dest_path, 'wb') as f:
        f.write(fh.read())

def move_drive_file(service, file_id, dest_folder_id):
    """Moves a file in Google Drive to the target folder."""
    # Retrieve current parent folders
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents', []))
    
    # Update parents
    service.files().update(
        fileId=file_id,
        addParents=dest_folder_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()

def run_drive_ingestion(dry_run=False, force=False):
    """Runs ingestion scanning the Google Drive Inbox folder."""
    credentials_path = os.getenv("DRIVE_CREDENTIALS_FILE", "drive_credentials.json")
    inbox_id = os.getenv("DRIVE_INBOX_FOLDER_ID")
    archive_id = os.getenv("DRIVE_ARCHIVE_FOLDER_ID")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not inbox_id or not archive_id:
        print("❌ Error: DRIVE_INBOX_FOLDER_ID and DRIVE_ARCHIVE_FOLDER_ID must be set in .env.")
        sys.exit(1)
        
    try:
        service = get_drive_service(credentials_path)
    except Exception as e:
        print(f"❌ Error authenticating Google Drive: {e}")
        sys.exit(1)
        
    print(f"☁️ Scanning Google Drive Inbox (Folder ID: {inbox_id})...")
    # Query all files in the Inbox folder
    query = f"'{inbox_id}' in parents and trashed = false"
    results = service.files().list(
        q=query, fields="files(id, name, mimeType)"
    ).execute()
    files = results.get('files', [])
    
    if not files:
        print("📭 Google Drive Inbox is empty.")
        return
        
    print(f"📥 Found {len(files)} files to process.")
    os.makedirs(TEMP_RAW_DIR, exist_ok=True)
    
    for file in files:
        file_id = file['id']
        file_name = file['name']
        
        print(f"\n⚡ Processing file: {file_name} (ID: {file_id})")
        temp_file_path = os.path.join(TEMP_RAW_DIR, file_name)
        
        try:
            # Download file
            download_file_from_drive(service, file_id, temp_file_path)
            
            # Read bytes for hash
            with open(temp_file_path, "rb") as f:
                file_bytes = f.read()
            file_hash = calculate_sha256(file_bytes)
            
            # Check duplicate
            if is_already_ingested(file_hash) and not force:
                print(f"⏭️ File skipped: Content already ingested (Hash matches).")
                os.remove(temp_file_path)
                continue
                
            # Process parser
            success, account_id, message = process_file_content(
                temp_file_path, file_name, dry_run, gemini_api_key
            )
            
            if success:
                print(f"✅ Processing success: {message}")
                if not dry_run:
                    # Register success in ledger
                    register_ingestion(file_name, file_hash, "success", account_id, message)
                    # Move on Google Drive to Archive folder
                    move_drive_file(service, file_id, archive_id)
                    print(f"📦 Moved original to Google Drive Archive.")
            else:
                print(f"❌ Processing failed: {message}")
                if not dry_run:
                    # Register failure
                    register_ingestion(file_name, file_hash, "failed", account_id, message)
                    
        except Exception as e:
            print(f"💥 Exception processing file {file_name}: {e}")
        finally:
            # Cleanup local temp raw file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

def run_local_file_ingestion(local_path, dry_run=False, force=False):
    """Runs ingestion for a single local file (dry-run or direct import)."""
    if not os.path.exists(local_path):
        print(f"❌ Error: Local file not found at '{local_path}'")
        sys.exit(1)
        
    file_name = os.path.basename(local_path)
    print(f"\n⚡ Processing Local File: {file_name}")
    
    with open(local_path, "rb") as f:
        file_bytes = f.read()
    file_hash = calculate_sha256(file_bytes)
    
    # Check duplicate
    if is_already_ingested(file_hash) and not force:
        print(f"⏭️ File skipped: Content already ingested (Hash matches). Use --force to override.")
        return
        
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    success, account_id, message = process_file_content(
        local_path, file_name, dry_run, gemini_api_key
    )
    
    if success:
        print(f"✅ Processing success: {message}")
        if not dry_run:
            register_ingestion(file_name, file_hash, "success", account_id, message)
    else:
        print(f"❌ Processing failed: {message}")
        if not dry_run:
            register_ingestion(file_name, file_hash, "failed", account_id, message)

def main():
    parser = argparse.ArgumentParser(description="Finances Ingestion Orchestrator (Google Drive / Local)")
    parser.add_argument("--dry-run", action="store_true", help="Process and validate files without committing changes or moving files in Drive")
    parser.add_argument("--force", action="store_true", help="Ignore ingestion database hashes and force re-processing")
    parser.add_argument("--file", help="Path to a single local file to process, bypassing Google Drive connection")
    
    args = parser.parse_args()
    
    if args.file:
        run_local_file_ingestion(args.file, args.dry_run, args.force)
    else:
        run_drive_ingestion(args.dry_run, args.force)

if __name__ == "__main__":
    main()
