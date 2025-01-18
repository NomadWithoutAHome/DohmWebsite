import os
import clr
clr.AddReference('System.IO')
clr.AddReference('System')
from System.IO import BinaryWriter, BinaryReader, FileStream, FileMode, FileAccess, SeekOrigin
from System import Array, String, Char
try:
    from .logger import get_logger
except ImportError:
    from utils.logging_config import app_logger as logger

class StringCrypto:
    # The exact same character arrays as in the game's SC class, but using C# arrays
    DICTIONARY = String("aAbcdEFgGijJklmnoOpPqrSUwXyZ234BCDfHIKMNQtuvWxz7@!#_=|}'68~`$%ehLRsTVY0159+{:?^&*()-/[];,<>.\\").ToCharArray()
    REFERENCES = String("aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ0123456789@~`!#$%^&*()_-=+/|[]{}';:,<>?.\\").ToCharArray()

    @staticmethod
    def encode(input_str):
        """Encrypts a string using the same character substitution as the game."""
        # input_str is already a C# String when coming from BinaryReader
        if not isinstance(input_str, str):
            array = input_str.ToCharArray()
        else:
            array = String(input_str).ToCharArray()
            
        text = String.Empty
        for i in range(len(array)):
            num = -1
            for c in StringCrypto.REFERENCES:
                num += 1
                if array[i] == c:
                    array[i] = StringCrypto.DICTIONARY[num]
                    num = -1
                    break
            text += array[i]
        return str(text)  # Convert back to Python string

    @staticmethod
    def decode(input_str):
        """Decrypts a string using the same character substitution as the game."""
        # input_str is already a C# String when coming from BinaryReader
        if not isinstance(input_str, str):
            array = input_str.ToCharArray()
        else:
            array = String(input_str).ToCharArray()
            
        text = String.Empty
        for i in range(len(array)):
            num = -1
            for c in StringCrypto.DICTIONARY:
                num += 1
                if array[i] == c:
                    array[i] = StringCrypto.REFERENCES[num]
                    num = -1
                    break
            text += array[i]
        return str(text)  # Convert back to Python string

    @staticmethod
    def save_wsdir(save_paths, filepath):
        """
        Saves the WSDir.txt file with encrypted save file paths.
        
        Args:
            save_paths (dict): Dictionary of save names to file paths
            filepath (str): Path where to save the WSDir.txt file
        """
        # Ensure all required save slots exist
        required_slots = {
            "autosaveLoad": "",  # Base autosave
            "save1Load": "",     # Base save slots 1-5
            "save2Load": "",
            "save3Load": "",
            "save4Load": "",
            "save5Load": "",
        }
        
        # Add any scenario-specific save slots from existing data
        for key in save_paths.keys():
            if key.startswith(("save", "autosave")) and key.endswith("Load"):
                required_slots[key] = ""
                
        # Update with provided values
        required_slots.update(save_paths)
        
        # Convert dictionary to string format: "key=value;key=value;" (note the trailing semicolon)
        content = String.Empty
        for k, v in required_slots.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ValueError("Both keys and values must be strings")
            content += f"{k}={v};"
        
        # Encrypt the content
        encrypted = StringCrypto.encode(content)
        
        # Write to file using BinaryWriter
        fs = None
        writer = None
        try:
            fs = FileStream(filepath, FileMode.Create)
            writer = BinaryWriter(fs)
            writer.Write(String(encrypted))  # Use Write(string) to match game's BinaryWriter.Write
        finally:
            if writer:
                writer.Close()
            if fs:
                fs.Close()

    @staticmethod
    def load_wsdir(filepath):
        """
        Loads and decrypts the WSDir.txt file.
        
        Args:
            filepath (str): Path to the WSDir.txt file
            
        Returns:
            dict: Dictionary of save names to file paths
        """
        if not os.path.exists(filepath):
            return {}
            
        # Read from file using BinaryReader
        fs = None
        reader = None
        try:
            fs = FileStream(filepath, FileMode.Open)
            reader = BinaryReader(fs)
            
            # Read all bytes and convert to string
            length = fs.Length
            bytes_array = Array.CreateInstance(Char, int(length))
            reader.Read(bytes_array, 0, int(length))
            encrypted = String(bytes_array)  # Create string directly from char array
            
            # Decrypt the text
            decrypted = StringCrypto.decode(encrypted)
            
            # Parse the key-value pairs
            result = {}
            pairs = String(decrypted).Split(Array[Char]([';']))
            for pair in pairs:
                if String(pair).Contains('='):
                    key_value = String(pair).Split(Array[Char](['=']))
                    if len(key_value) == 2:
                        result[str(key_value[0])] = str(key_value[1])
            return result
            
        finally:
            if reader:
                reader.Close()
            if fs:
                fs.Close() 