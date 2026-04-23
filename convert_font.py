import base64
import os

font_path = 'C:/Windows/Fonts/arial.ttf'
output_path = 'frontend/js/shared/font-arial.js'

if os.path.exists(font_path):
    with open(font_path, 'rb') as f:
        b64_data = base64.b64encode(f.read()).decode()
    
    with open(output_path, 'w') as out:
        out.write('window.arialBase64 = "')
        out.write(b64_data)
        out.write('";')
    print(f"Font converted successfully to {output_path}")
else:
    print(f"Error: Font not found at {font_path}")
