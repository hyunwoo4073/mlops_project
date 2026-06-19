import re


def clean_text(text: str) -> str:
    if text is None:
        return ""

    text = str(text)

    # HTML 태그 제거
    text = re.sub(r"<[^>]+>", " ", text)

    # 개행/탭 제거
    text = re.sub(r"[\n\r\t]", " ", text)

    # 특수문자 일부 정리
    text = re.sub(r"[^0-9a-zA-Z가-힣+#./\-\s]", " ", text)

    # 공백 정리
    text = re.sub(r"\s+", " ", text).strip()

    return text
