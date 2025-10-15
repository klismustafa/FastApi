FastApi simple register and log in interface.
It is required to create an ENV file for this to work properly. 
Copy the blueprint below and insert your own data. For email password make sure you are using 2FA and an app pasword for it to work.
SECRET_KEY="Ur key"

ALGORITHM="HS256"

ACCESS_TOKEN_EXPIRE_MINUTES=30

MAIL_USERNAME=Your email

MAIL_PASSWORD=App password(Remove the spaces)

MAIL_FROM=your email

MAIL_PORT=465

MAIL_SERVER=smtp.gmail.com

MAIL_STARTTLS=False

MAIL_SSL_TLS=True

To initialise the FASTAPI use uvicorn main:app --reload in terminal
