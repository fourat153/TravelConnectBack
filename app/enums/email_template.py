from enum import Enum


class EmailTemplate(str, Enum):
    resetpassword = 'resetPassword'
    confirmaccount = 'confirmAccount'
    invitation = 'invitation'