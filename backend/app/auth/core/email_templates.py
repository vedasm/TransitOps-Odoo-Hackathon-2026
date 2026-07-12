def verification_email_html(user_name: str, verify_url: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 40px;">
      <div style="max-width: 520px; margin: auto; background: white; border-radius: 8px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <h2 style="color: #333;">Hi {user_name},</h2>
        <p style="color: #555; font-size: 15px;">
          Thanks for signing up! Please verify your email address by clicking the button below.
          This link expires in <strong>24 hours</strong>.
        </p>
        <div style="text-align: center; margin: 32px 0;">
          <a href="{verify_url}"
             style="background-color: #4F46E5; color: white; padding: 14px 28px;
                    text-decoration: none; border-radius: 6px; font-size: 15px; font-weight: bold;">
            Verify Email
          </a>
        </div>
        <p style="color: #888; font-size: 13px;">
          Or copy and paste this link into your browser:<br/>
          <a href="{verify_url}" style="color: #4F46E5;">{verify_url}</a>
        </p>
        <p style="color: #aaa; font-size: 12px; margin-top: 32px;">
          If you didn't create an account, you can safely ignore this email.
        </p>
      </div>
    </body>
    </html>
    """


def password_reset_email_html(user_name: str, reset_url: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 40px;">
      <div style="max-width: 520px; margin: auto; background: white; border-radius: 8px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <h2 style="color: #333;">Hi {user_name},</h2>
        <p style="color: #555; font-size: 15px;">
          We received a request to reset your password. Click the button below to choose a new one.
          This link expires in <strong>1 hour</strong>.
        </p>
        <div style="text-align: center; margin: 32px 0;">
          <a href="{reset_url}"
             style="background-color: #DC2626; color: white; padding: 14px 28px;
                    text-decoration: none; border-radius: 6px; font-size: 15px; font-weight: bold;">
            Reset Password
          </a>
        </div>
        <p style="color: #888; font-size: 13px;">
          Or copy and paste this link into your browser:<br/>
          <a href="{reset_url}" style="color: #DC2626;">{reset_url}</a>
        </p>
        <p style="color: #aaa; font-size: 12px; margin-top: 32px;">
          If you didn't request a password reset, you can safely ignore this email.
        </p>
      </div>
    </body>
    </html>
    """