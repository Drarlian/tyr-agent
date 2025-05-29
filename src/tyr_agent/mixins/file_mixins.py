from typing import Optional, Union
from io import BytesIO
import base64
import mimetypes


class FileMixin:
    def convert_item_to_gemini_file(self, file: Union[str, BytesIO], file_name: str) -> dict:
        """
        Converte um path, base64 ou BytesIO para o formato ideal para ser enviado na requisição do Gemini.
        :param file: Arquivo a ser enviado, podendo ser path, base64 ou BytesIO.
        :param file_name: Nome do arquivo a ser enviado.
        :return: Retorna um dicionário no formato ideal para ser enviado via Gemini.
        """
        try:
            # Obtendo os bytes do arquivo:
            if isinstance(file, str):
                bytes_file = self.__convert_base64_to_bytes(file)  # base64
                if bytes_file is None:  # path
                    with open(file, "rb") as f:
                        bytes_file = f.read()
            elif isinstance(file, BytesIO):
                bytes_file = file.read()
            else:
                raise ValueError("Tipo de arquivo não suportado.")

            # Obtendo o mime_type do arquivo:
            mime_type = self.__detect_mime_type(file_name)

            # Construindo o formato do Gemini para arquivos:
            file_format = {
                    "mime_type": mime_type,
                    "data": bytes_file
            }

            if mime_type == "application/octet-stream":
                raise ValueError(f"Tipo MIME não suportado ou não reconhecido para o arquivo '{file_name}'.")

            return file_format
        except Exception:
            return {}

    def __detect_mime_type(self, file_name: str) -> str:
        from pathlib import Path

        mime_map = {
            ".pdf": "application/pdf",
            ".csv": "text/csv",
            ".txt": "text/plain",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".json": "application/json",
        }

        ext = Path(file_name).suffix.lower()
        if ext in mime_map:
            return mime_map[ext]

        mime_type, _ = mimetypes.guess_type(file_name)
        return mime_type or "application/octet-stream"

    def __convert_base64_to_bytes(self, string_base64: str) -> Optional[bytes]:
        """
        Tenta decodificar um conteúdo base64 (com ou sem header).
        :param string_base64: String a ser validada.
        :return: Retorna os bytes ou levanta None se não for válido.
        """
        try:
            if string_base64.startswith("data:"):
                header, b64data = string_base64.split(",", 1)
            else:
                b64data = string_base64

            # Validando o tamanho e padding: (b64 precisa ser múltiplo de 4)
            if len(b64data.strip()) % 4 != 0:
                b64data += '=' * (4 - len(b64data.strip()) % 4)

            # Decodificando a string base64 (b64data) para bytes e Validando se a string é um base64 válido e bem formado:
            return base64.b64decode(b64data, validate=True)
        except Exception:
            # print(f'[ERROR] - __detect_base64: {type(e).__name__}: {e}')
            return None
