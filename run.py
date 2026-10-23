"""
OmniHealth-Rec — Application Entry Point
"""

import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"\n * OmniHealth running at: http://127.0.0.1:{port}\n")
    app.run(debug=True, host='0.0.0.0', port=port)
