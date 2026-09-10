from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users.
    Handles password confirmation, optional profile fields, and email uniqueness.
    """
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    company = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'phone', 'company')
        extra_kwargs = {
            # Email is required for registration
            'email': {'required': True}
        }

    def validate_email(self, value):
        """
        I added this method to make sure no two users can register with the
        same email address. Django's default User model doesn't enforce unique
        emails, so I'm doing this check manually here. I also made the check
        case-insensitive (iexact) so that 'Test@x.com' and 'test@x.com' are
        treated as the same email.
        """
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists. Please use a different email."
            )
        return value

    def validate(self, attrs):
        """
        I use this method to check that both password fields match.
        If they don't match, I raise a validation error that the frontend can display.
        """
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password is not matching!"})
        return attrs

    def create(self, validated_data):
        """
        I create the user manually here because I need to extract the extra
        fields (phone, company) and save them into the UserProfile model,
        which is automatically created by a signal when the user is created.
        """
        # Extract the values we need from validated_data
        username = validated_data.get('username')
        email = validated_data.get('email')
        password = validated_data.get('password')
        phone = validated_data.get('phone', '')
        company = validated_data.get('company', '')

        # I use create_user instead of create so the password gets hashed properly
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # The profile is created automatically by a signal in models.py,
        # so here I just update its optional fields.
        profile = user.profile
        if phone:
            profile.phone = phone
        if company:
            profile.company = company
        profile.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserProfile model.
    Only exposes phone and company (the user is linked through the parent serializer).
    """
    class Meta:
        model = UserProfile
        fields = ('phone', 'company')


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer used to return user data (e.g., in login response or profile page).
    Includes the nested profile serializer so the frontend can easily access
    phone and company without making extra requests.
    """
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'profile')