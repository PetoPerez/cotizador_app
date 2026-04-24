import bcrypt
pwd = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
print(pwd)
