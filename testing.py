import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# Configure API key
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = env.Mail_Api_Key

api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
    sib_api_v3_sdk.ApiClient(configuration)
)

# Email content
sender = {"email": env.Mail_Sender_Email, "name": "My App"}
to = [{"email": env.Mail_Recipient_Email, "name": "User"}]

send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
    to=to,
    sender=sender,
    subject="Notification from App",
    html_content="""
    <h2>Hello!</h2>
    <p>You have a new notification.</p>
    """
)

try:
    response = api_instance.send_transac_email(send_smtp_email)
    print(response)

except ApiException as e:
    print("Error:", e)