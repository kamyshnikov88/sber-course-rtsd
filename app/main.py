from flask import Flask, request, jsonify
import traceback

from app.torch_utils import transform_image, get_prediction
# from torch_utils import transform_image, get_prediction
app = Flask(__name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(name):
    return '.' in name and name.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        file = request.files.get('file')
        if file is None or file.filename == '':
            return jsonify({'error': 'no file'})
        if not allowed_file(file.filename):
            return jsonify({'error': 'not supported extension'})
        try:
            img_bytes = file.read()
            tensor = transform_image(img_bytes)
            predictions = get_prediction(tensor)
            data = {'predictions': predictions}
            return jsonify(data)
        except Exception:
            return jsonify({'error': traceback.format_exc()})