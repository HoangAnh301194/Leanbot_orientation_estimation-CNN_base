import os
import base64
from email.message import EmailMessage
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from mcp.server.fastmcp import FastMCP

# Scopes cho phép đọc, gửi và sửa email
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.json')

# Tạo MCP Server
mcp = FastMCP("Gmail MCP Server")

def get_gmail_service():
    """Hàm lấy hoặc khởi tạo Google Auth credentials"""
    creds = None
    # Token lưu trữ lịch sử đăng nhập
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
    # Nếu chưa có credential hợp lệ thì mở tab xác thực
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Lưu lại token cho những lần chạy sau
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return build('gmail', 'v1', credentials=creds)


@mcp.tool()
def search_emails(query: str = "", max_results: int = 10) -> str:
    """
    Tìm kiếm email trong hộp thư dựa trên truy vấn.
    
    Args:
        query: Chuỗi truy vấn chuẩn của Gmail (vd: "is:unread", "from:abc@gmail.com", "subject:hello").
        max_results: Số lượng email tối đa trả về.
    """
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "Không tìm thấy email nào phù hợp."
            
        output = []
        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']
            ).execute()
            
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Không có chủ đề')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Không rõ người gửi')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Không rõ ngày')
            
            output.append(f"ID: {msg['id']} | Date: {date} | From: {sender} | Subject: {subject}")
            
        return "\n".join(output)
    except Exception as e:
        return f"Lỗi khi tìm kiếm email: {str(e)}"


@mcp.tool()
def read_email(message_id: str) -> str:
    """
    Đọc nội dung chi tiết của một email.
    
    Args:
        message_id: ID của email (lấy từ kết quả tìm kiếm).
    """
    try:
        service = get_gmail_service()
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        
        # Chỉ lấy snippet cho ngắn gọn hoặc cố gắng parse body
        snippet = msg.get('snippet', '')
        
        # Parse thông tin Header
        headers = msg['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Không có chủ đề')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Không rõ')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Không rõ ngày')
        
        return f"From: {sender}\nDate: {date}\nSubject: {subject}\n\nSnippet:\n{snippet}\n"
    except Exception as e:
        return f"Lỗi khi đọc email: {str(e)}"


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """
    Gửi một email mới.
    
    Args:
        to: Địa chỉ email người nhận.
        subject: Chủ đề email.
        body: Nội dung email.
    """
    try:
        service = get_gmail_service()
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to
        message['Subject'] = subject
        
        # Base64 encode
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        send_message = service.users().messages().send(userId="me", body=create_message).execute()
        return f"Email đã được gửi thành công! Message ID: {send_message['id']}"
    except Exception as e:
        return f"Lỗi khi gửi email: {str(e)}"


if __name__ == "__main__":
    import sys
    # In ra stderr để không làm hỏng giao thức stdio của MCP
    print("Đang kiểm tra xác thực Gmail...", file=sys.stderr)
    try:
        # Gọi thử để bắt buộc luồng đăng nhập chạy (nếu chưa có token)
        get_gmail_service()
        print("Xác thực thành công. Khởi chạy Gmail MCP Server...", file=sys.stderr)
    except Exception as e:
        print(f"Lỗi xác thực: {e}", file=sys.stderr)
        sys.exit(1)
        
    mcp.run(transport='stdio')
