import os

bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"
workers = 4
timeout = 120
accesslog = '-'
errorlog = '-' 