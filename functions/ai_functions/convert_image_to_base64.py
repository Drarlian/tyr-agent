import base64


def image_to_base64(caminho_imagem):
    """
    Converte uma imagem para uma string em base64.

    Parâmetros:
        caminho_imagem (str): Caminho do arquivo da imagem (ex: 'imagem.jpg').

    Retorna:
        str: String base64 da imagem.
    """
    try:
        with open(caminho_imagem, "rb") as imagem:
            imagem_bytes = imagem.read()
            imagem_base64 = base64.b64encode(imagem_bytes).decode('utf-8')
            return imagem_base64
    except FileNotFoundError:
        print(f"Arquivo não encontrado: {caminho_imagem}")
    except Exception as e:
        print(f"Erro ao converter imagem: {e}")
