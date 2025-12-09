from typing import Optional, Union, Tuple
from io import BytesIO


class GPTFileMixin:
    SUPPORTED_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf"
    }

    def convert_item_to_gpt_model(self, file: Union[str, bytes, BytesIO], file_name: str) -> Optional[Tuple[str, str]]:
        """
        Converte um arquivo (path, bytes ou BytesIO) para base64 com prefixo data URL (data:image/png;base64,...).
        Suporta apenas imagens.
        :param file: Caminho para o arquivo, bytes ou BytesIO.
        :param file_name: Nome original do arquivo (usado para detectar o mime type).
        :return: Tupla de Strings onde 0: base64 formatada como data URL; 1: Nome do arquivo.
        :raises: ValueError para tipos de arquivo não suportados ou erros de leitura.
        """
        import base64

        # Detecta o mime type com base no nome
        mime_type = self.__detect_mime_type(file_name)

        if mime_type not in self.SUPPORTED_TYPES:
            return None

        # Obtendo os bytes do arquivo:
        bytes_file = self.__get_file_bytes(file)
        if not bytes_file:
            return None

        # Codificando em base64:
        b64_string = base64.b64encode(bytes_file).decode()

        # Retorna no formato data URL
        return f"data:{mime_type};base64,{b64_string}", file_name

    def __detect_mime_type(self, file_name: str) -> str:
        """
        Detecta o tipo do arquivo informado baseado no nome dele e retorno mime type dele.
        :param file_name: Nome do arquivo a ser analisado.
        :return: Retorna o tipo mime do arquivo recebido.
        """
        import mimetypes
        from pathlib import Path

        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".pdf": "application/pdf"
        }

        ext = Path(file_name).suffix.lower()
        if ext in mime_map:
            return mime_map[ext]

        mime_type, _ = mimetypes.guess_type(file_name)
        return mime_type or "application/octet-stream"

    def __get_file_bytes(self, file: Union[str, BytesIO]) -> Optional[bytes]:
        """
        Pega os bytes de um arquivo, seja via path ou BytesIO.
        :param file: Arquivo que terá seus bytes extraídos.
        :return: Retorna os bytes do arquivo.
        """
        if isinstance(file, str):
            try:
                with open(file, "rb") as f:
                    return f.read()
            except Exception:
                return None
        elif isinstance(file, BytesIO):
            return file.read()
        elif isinstance(file, bytes):
            return file
        return None
