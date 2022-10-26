#!/usr/bin/env python3
"""
A client to smooth over process of common authentication scenarios
using AWS Cognito. Intended to be used within an interactive terminal 
environment (e.g. Python Notebook, CLI).
"""

from enum import Enum
from typing import TYPE_CHECKING, Optional
import getpass
import logging
import os

import boto3
from pydantic import BaseSettings, Field


if TYPE_CHECKING:
    from mypy_boto3_cognito_idp.client import CognitoIdentityProviderClient
    from mypy_boto3_cognito_identity.client import CognitoIdentityClient
    from mypy_boto3_cognito_idp.type_defs import InitiateAuthResponseTypeDef


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)


class ChallengeType(str, Enum):
    SMS_MFA = "SMS_MFA"
    SOFTWARE_TOKEN_MFA = "SOFTWARE_TOKEN_MFA"
    SELECT_MFA_TYPE = "SELECT_MFA_TYPE"
    MFA_SETUP = "MFA_SETUP"
    PASSWORD_VERIFIER = "PASSWORD_VERIFIER"
    CUSTOM_CHALLENGE = "CUSTOM_CHALLENGE"
    DEVICE_SRP_AUTH = "DEVICE_SRP_AUTH"
    DEVICE_PASSWORD_VERIFIER = "DEVICE_PASSWORD_VERIFIER"
    ADMIN_NO_SRP_AUTH = "ADMIN_NO_SRP_AUTH"
    NEW_PASSWORD_REQUIRED = "NEW_PASSWORD_REQUIRED"


class AuthFailure(Exception):
    ...


class CognitoClient(BaseSettings):
    # username can be either email address or sub
    username: str = Field(
        default_factory=lambda: input("Enter your Cognito username: "),
        min_length=1,
        max_length=128,
    )
    # cognito app client identifier
    client_id: str = Field(
        description="ID of Cognito client associated with Cognito identity pool",
        repr=False,
    )
    client_region: str = Field(
        default="us-west-2",
        description="Cognito user pool region",
    )
    user_pool_id: str = Field(
        description="ID of Cognito user pool",
        repr=False,
    )
    identity_pool_id: str = Field(
        description="ID of Cognito identity pool",
        repr=False,
    )

    # Manually provide an access token to skip logging-in when the client is initiated.
    access_token: Optional[str] = None
    id_token: Optional[str] = None

    # Controls whether a we should automatically attempt to resolve challenges
    resolve_challenges: bool = True

    class Config:
        env_file = ".env"

    @property
    def cognito_idp_client(self) -> "CognitoIdentityProviderClient":
        return boto3.client("cognito-idp", region_name=self.client_region)

    @property
    def cognito_identity_client(self) -> "CognitoIdentityClient":
        return boto3.client("cognito-identity", region_name=self.client_region)

    def login(self, password: Optional[str] = None) -> "InitiateAuthResponseTypeDef":
        password = password or os.environ.get("password") or getpass.getpass(prompt="Enter your Cognito password: ")

        try:
            response = self.cognito_idp_client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={"USERNAME": self.username, "PASSWORD": password},
            )
        except self.cognito_idp_client.exceptions.PasswordResetRequiredException:
            if not self.resolve_challenges:
                raise

            # print("Password reset required. Check your email for a confirmation code.")
            return self._resolve_password_reset()

        if challenge_name := response.get("ChallengeName"):
            if self.resolve_challenges:
                response = self._resolve_auth_challenge(
                    ChallengeName=challenge_name, Session=response["Session"]
                )
            else:
                raise AuthFailure(
                    f"Received auth challenge {challenge_name}. Aborting."
                )

        if "AuthenticationResult" not in response:
            raise AuthFailure(f"Failed to authenticate. Response: \n{response}")

        self.access_token = response["AuthenticationResult"]["AccessToken"]
        self.id_token = response["AuthenticationResult"]["IdToken"]
        return response

    def _resolve_auth_challenge(
        self,
        ChallengeName: ChallengeType,
        Session: str,
    ) -> "InitiateAuthResponseTypeDef":
        """
        If Cognito responds with an auth challenge, prompt user to submit information
        necessary to complete login.
        """
        ChallengeResponse = {"USERNAME": self.username}
        if ChallengeName == ChallengeType.NEW_PASSWORD_REQUIRED:
            ChallengeResponse["NEW_PASSWORD"] = getpass.getpass(
                "A new password is required. Please provide a new password: "
            )
        elif ChallengeName == ChallengeType.SMS_MFA:
            ChallengeResponse["SMS_MFA_CODE"] = input(
                "Please provide the code sent to you via SMS: "
            )
        elif ChallengeName == ChallengeType.SMS_MFA:
            ChallengeResponse["SMS_MFA_CODE"] = input(
                "Please provide the code sent to you via SMS: "
            )
        else:
            raise AuthFailure(
                f"Unexpected auth challenge encountered: '{ChallengeName}'. "
                "Unable to automatically resolve issue."
            )

        response = self.cognito_idp_client.respond_to_auth_challenge(
            ClientId=self.client_id,
            Session=Session,
            ChallengeName=ChallengeName,
            ChallengeResponses=ChallengeResponse,
        )

        return response

    def _init_password_reset(self):
        self.cognito_idp_client.resend_confirmation_code(
            ClientId=self.client_id, Username=self.username
        )

    def _resolve_password_reset(
        self, confirmation_code=None, new_password=None
    ) -> "InitiateAuthResponseTypeDef":
        """
        Complete password reset flow.
        """
        confirmation_code = confirmation_code or input("Confirmation code: ")
        new_password = new_password or getpass.getpass("New password: ")
        response = self.cognito_idp_client.confirm_forgot_password(
            ClientId=self.client_id,
            Username=self.username,
            ConfirmationCode=confirmation_code,
            Password=new_password,
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise AuthFailure(f"Failed to reset password. Response: \n{response}")

        logger.info("Successfully set password.")

        return self.login(password=new_password)

    def get_user(self):
        return self.cognito_idp_client.get_user(AccessToken=self.access_token)

    def get_aws_credentials(self):
        if not self.id_token:
            raise AuthFailure("You must first login before getting credentials.")

        region = self.identity_pool_id.split(":")[0]
        logins = {
            f"cognito-idp.{region}.amazonaws.com/{self.user_pool_id}": self.id_token
        }

        identity_id = self.cognito_identity_client.get_id(
            IdentityPoolId=self.identity_pool_id,
            Logins=logins,
        )["IdentityId"]

        return self.cognito_identity_client.get_credentials_for_identity(
            IdentityId=identity_id,
            Logins=logins,
        )["Credentials"]


if __name__ == "__main__":
    """
    Running this directly will simply log in a user and return their token.
    """
    client = CognitoClient()
    client.login()
    print(client.access_token)