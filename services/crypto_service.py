import clr
clr.AddReference('System.Security')
clr.AddReference('System.IO')
from System.Security.Cryptography import RijndaelManaged, CipherMode, PaddingMode
from System.Text import Encoding
from System.IO import BinaryReader, BinaryWriter, MemoryStream, FileStream, FileMode, FileAccess
import base64
from Crypto.Cipher import AES
import json
import UnityPy
try:
    from .logger import get_logger
except ImportError:
    from logger import get_logger

# Get module logger
logger = get_logger(__name__)

class SaveCrypto:
    # Encryption keys
    SAVE_KEY = "e1n6c3dy4n9k2ey5"  # Key for save files
    REFDATA_KEY = "e7nc3r2e6f8k2e0y"  # Key for reference data

    @staticmethod
    def decrypt(data: bytes | str, key: str = None, filepath: str = None) -> str:
        """Decrypt data using the appropriate key based on file type"""
        if filepath and filepath.lower().endswith('.assets'):
            key = SaveCrypto.REFDATA_KEY
            # Handle WSREF data from assets file
            try:
                # Data is already a string from TextAsset
                encrypted_str = data if isinstance(data, str) else data.decode('utf-8')
                # Remove padding characters
                encrypted_str = encrypted_str[len(encrypted_str) % 4:]
                
                # Create RijndaelManaged with game's settings
                rijndael = RijndaelManaged()
                rijndael.Key = Encoding.UTF8.GetBytes(key)
                rijndael.Mode = CipherMode.ECB
                rijndael.Padding = PaddingMode.PKCS7
                rijndael.BlockSize = 128
                
                # Convert base64 string to bytes
                from System import Convert
                encrypted = Convert.FromBase64String(encrypted_str)
                
                # Create decryptor and decrypt
                decryptor = rijndael.CreateDecryptor()
                decrypted = decryptor.TransformFinalBlock(encrypted, 0, len(encrypted))
                
                # Convert back to string using UTF8
                return Encoding.UTF8.GetString(decrypted)
                
            except Exception as e:
                logger.error(f"Error decrypting WSREF data: {str(e)}")
                raise
        else:
            # Default to save file handling
            key = key or SaveCrypto.SAVE_KEY
            try:
                logger.debug("Decrypting save data...")
                logger.debug(f"Input data length: {len(data)} bytes")
                
                # Read from binary stream like the game does
                mem_stream = MemoryStream(data)
                binary_reader = BinaryReader(mem_stream)
                encrypted_str = binary_reader.ReadString()
                logger.debug(f"Read string length: {len(encrypted_str)}")
                
                # Create RijndaelManaged with game's settings
                rijndael = RijndaelManaged()
                rijndael.Key = Encoding.UTF8.GetBytes(key)
                rijndael.Mode = CipherMode.ECB
                rijndael.Padding = PaddingMode.PKCS7
                rijndael.BlockSize = 128
                
                # Convert base64 string to bytes using .NET's Convert
                from System import Convert
                encrypted = Convert.FromBase64String(encrypted_str)
                logger.debug(f"Decoded data length: {len(encrypted)} bytes")
                
                # Create decryptor and decrypt
                decryptor = rijndael.CreateDecryptor()
                decrypted = decryptor.TransformFinalBlock(encrypted, 0, len(encrypted))
                
                # Convert back to string using UTF8
                result = Encoding.UTF8.GetString(decrypted)
                logger.debug("Successfully decoded using UTF8")
                
                # Log a sample of the decrypted data
                sample_size = min(200, len(result))
                logger.debug(f"First {sample_size} chars of decrypted data: {result[:sample_size]}")
                
                return result
                
            except Exception as e:
                logger.error(f"Error decrypting save data: {str(e)}")
                raise

    @staticmethod
    def encrypt(data: str, key: str = None, filepath: str = None) -> bytes:
        """Encrypt data using the appropriate key based on file type"""
        if filepath and filepath.lower().endswith('.assets'):
            key = SaveCrypto.REFDATA_KEY
            # Handle WSREF data encryption
            try:
                # Create RijndaelManaged with game's settings
                rijndael = RijndaelManaged()
                rijndael.Key = Encoding.UTF8.GetBytes(key)
                rijndael.Mode = CipherMode.ECB
                rijndael.Padding = PaddingMode.PKCS7
                rijndael.BlockSize = 128
                
                # Convert text to bytes using UTF8
                bytes_to_encrypt = Encoding.UTF8.GetBytes(data)
                
                # Create encryptor and encrypt
                encryptor = rijndael.CreateEncryptor()
                encrypted = encryptor.TransformFinalBlock(bytes_to_encrypt, 0, len(bytes_to_encrypt))
                
                # Convert to Base64 string using .NET's Convert
                from System import Convert
                result = Convert.ToBase64String(encrypted)
                return result.encode('utf-8')
                
            except Exception as e:
                logger.error(f"Error encrypting WSREF data: {str(e)}")
                raise
        else:
            # Default to save file handling
            key = key or SaveCrypto.SAVE_KEY
            try:
                logger.debug("Encrypting text...")
                logger.debug(f"Raw data length: {len(data)} bytes")
                
                # Create RijndaelManaged with game's settings
                rijndael = RijndaelManaged()
                rijndael.Key = Encoding.UTF8.GetBytes(key)
                rijndael.Mode = CipherMode.ECB
                rijndael.Padding = PaddingMode.PKCS7
                rijndael.BlockSize = 128
                
                # Convert text to bytes using UTF8
                bytes_to_encrypt = Encoding.UTF8.GetBytes(data)
                logger.debug(f"UTF8 bytes length: {len(bytes_to_encrypt)} bytes")
                
                # Create encryptor and encrypt
                encryptor = rijndael.CreateEncryptor()
                encrypted = encryptor.TransformFinalBlock(bytes_to_encrypt, 0, len(bytes_to_encrypt))
                
                # Convert to Base64 string using .NET's Convert
                from System import Convert
                result = Convert.ToBase64String(encrypted)
                
                # Write to binary stream like the game does
                mem_stream = MemoryStream()
                binary_writer = BinaryWriter(mem_stream)
                binary_writer.Write(result)
                binary_writer.Flush()
                
                # Get the bytes
                mem_stream.Position = 0
                output = bytes(mem_stream.ToArray())
                
                logger.debug(f"Final output length: {len(output)} bytes")
                return output
                
            except Exception as e:
                logger.error(f"Error encrypting save data: {str(e)}")
                raise

    @staticmethod
    def extract_refdata(filepath: str) -> dict:
        """Extract reference data from resources.assets file"""
        import UnityPy
        
        # Load the assets file
        env = UnityPy.load(filepath)
        logger.debug("Loaded assets file")
        
        # Find the WSREFDATA TextAsset
        wsrefdata = None
        for obj in env.objects:
            if obj.type.name == "TextAsset":
                data = obj.read()
                logger.debug(f"  Name: {data.m_Name}")
                if data.m_Name == "WSREFDATA":
                    logger.debug("Found WSREFDATA!")
                    wsrefdata = data
                    break
                    
        if not wsrefdata:
            raise ValueError("Could not find WSREFDATA in assets file")
            
        # Get the encrypted bytes
        encrypted_bytes = wsrefdata.m_Script
        
        # Decrypt the data
        decrypted_json = SaveCrypto.decrypt(encrypted_bytes, filepath=filepath)
        
        # Parse JSON
        return json.loads(decrypted_json)
    
