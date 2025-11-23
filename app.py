from flask import Flask, render_template, request, redirect, url_for, session, make_response
import requests
import os
import base64

# Khởi tạo Flask App
app = Flask(__name__)

# --- CẤU HÌNH QUAN TRỌNG (Sử dụng Biến Môi Trường Vercel) ---
# Biến FLASK_SECRET_KEY: Bắt buộc để bảo mật session. KHÔNG ĐƯỢC hardcode vào đây.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key_for_dev') 

# Biến VERCEL_API_URL: URL API Backend đã deploy (ví dụ: https://rice-detector-api-xyz.vercel.app/api)
API_BASE_URL = os.environ.get('VERCEL_API_URL', 'https://YOUR-BACKEND-API-URL.vercel.app/api')


# --- DỮ LIỆU DEMO CHO ĐĂNG NHẬP ---
# Trong môi trường sản phẩm, bạn phải dùng cơ chế xác thực an toàn hơn (ví dụ: Firebase Auth)
DEMO_USER = "user_demo"
DEMO_PASS = "Test@123456" 

# --- HÀM XÁC THỰC PHIÊN ---
def is_authenticated():
    """Kiểm tra xem người dùng đã đăng nhập chưa."""
    return 'username' in session

# --- ROUTE 1: LOGIN (Trang chủ) ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if is_authenticated():
        # Nếu đã đăng nhập, chuyển hướng ngay đến trang dự đoán
        return redirect(url_for('predict_page'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == DEMO_USER and password == DEMO_PASS:
            session['username'] = username
            # Đặt cookie để đánh dấu phiên (Hữu ích cho các script client-side)
            response = make_response(redirect(url_for('predict_page')))
            response.set_cookie('session_active', 'true', httponly=True)
            return response
        else:
            error = "Thông tin đăng nhập không hợp lệ. Vui lòng thử lại."

    # Render trang login.html (cần đặt trong thư mục templates/)
    return render_template('login.html', error=error)

# --- ROUTE 2: PREDICT (Trang dự đoán) ---
@app.route('/predict', methods=['GET', 'POST'])
def predict_page():
    if not is_authenticated():
        # Nếu chưa đăng nhập, chuyển hướng về trang login
        return redirect(url_for('login'))

    result_image = None
    message = None
    disease_details = None

    if request.method == 'POST':
        # 1. Kiểm tra file ảnh
        if 'image' not in request.files or not request.files['image'].filename:
            message = "Lỗi: Vui lòng chọn một file ảnh."
            return render_template('predict.html', message=message)

        image_file = request.files['image']

        # 2. Kiểm tra URL API đã được cấu hình chưa
        if 'YOUR-BACKEND-API-URL' in API_BASE_URL:
            message = "Lỗi cấu hình: Vui lòng cập nhật biến môi trường VERCEL_API_URL!"
            return render_template('predict.html', message=message)

        # 3. Gửi ảnh đến Vercel API Backend
        try:
            # Gửi file ảnh trực tiếp qua FormData
            # (tên field 'image' phải khớp với tên request.files['image'] ở Backend)
            files = {'image': (image_file.filename, image_file.stream, image_file.content_type)}
            
            # Tăng timeout vì mô hình AI cần thời gian xử lý
            api_response = requests.post(API_BASE_URL, files=files, timeout=45) 
            api_response.raise_for_status() # Báo lỗi nếu status code là 4xx hoặc 5xx

            result_data = api_response.json()
            
            # Xử lý Base64: loại bỏ tiền tố nếu có
            base64_full = result_data.get('result_image_base64', '')
            # Lấy phần data sau dấu phẩy (nếu có tiền tố data:image/jpeg;base64,)
            base64_data = base64_full.split(',')[1] if ',' in base64_full and 'base64' in base64_full else base64_full
            
            # Cập nhật kết quả để render ra predict.html
            result_image = base64_data
            message = result_data.get('message', 'Dự đoán hoàn tất.')
            disease_details = result_data.get('disease_details', [])

        except requests.exceptions.RequestException as e:
            # Xử lý lỗi kết nối hoặc HTTP
            print(f"API Request Error: {e}")
            message = f"Lỗi kết nối API: {e}. Đảm bảo VERCEL_API_URL đúng và Backend đang hoạt động."
        except Exception as e:
            # Xử lý lỗi khác (JSON parsing, v.v.)
            print(f"General Prediction Error: {e}")
            message = f"Lỗi dự đoán chung: {e}."
            
    # Render trang predict.html với kết quả (nếu có)
    return render_template(
        'predict.html', 
        result_image=result_image, 
        message=message,
        disease_details=disease_details
    )

# --- ROUTE 3: LOGOUT ---
@app.route('/logout')
def logout():
    session.pop('username', None)
    # Xóa cookie phiên
    response = make_response(redirect(url_for('login')))
    response.set_cookie('session_active', '', expires=0, httponly=True)
    return response

# Dòng này không cần thiết khi deploy lên Vercel
# if __name__ == '__main__':
#     app.run(debug=True)
