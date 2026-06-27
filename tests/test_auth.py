import unittest
from unittest.mock import patch

from backend.auth.auth import hash_password, verify_password


class AuthPasswordHandlingTests(unittest.TestCase):
    def test_hash_password_truncates_password_before_hashing(self):
        long_password = "a" * 80

        with patch("backend.auth.auth.pwd_context.hash", return_value="hashed") as mock_hash:
            result = hash_password(long_password)

        self.assertEqual(result, "hashed")
        mock_hash.assert_called_once_with(long_password[:72])

    def test_hash_password_truncates_to_72_bytes_before_hashing(self):
        long_password = "é" * 40

        with patch("backend.auth.auth.pwd_context.hash", return_value="hashed") as mock_hash:
            result = hash_password(long_password)

        self.assertEqual(result, "hashed")
        mock_hash.assert_called_once_with("é" * 36)

    def test_verify_password_truncates_plain_password_before_verifying(self):
        long_password = "b" * 80
        hashed_password = "hashed"

        with patch("backend.auth.auth.pwd_context.verify", return_value=True) as mock_verify:
            result = verify_password(long_password, hashed_password)

        self.assertTrue(result)
        mock_verify.assert_called_once_with(long_password[:72], hashed_password)


if __name__ == "__main__":
    unittest.main()
