"""Tests para RegexDetector."""

from umcp.pipeline.detectors.regex_detector import RegexDetector


def test_detect_nhc():
    """NHC español debe detectarse."""
    d = RegexDetector()
    # El NHC debe tener exactamente 4 dígitos + 2 letras
    ents = d.detect("El paciente tiene NHC 1234AB")
    nhc = [e for e in ents if e.type == "NHC"]
    assert len(nhc) == 1
    assert nhc[0].text == "1234AB"


def test_detect_dni():
    """DNI español debe detectarse."""
    d = RegexDetector()
    ents = d.detect("DNI 12345678Z")
    dni = [e for e in ents if e.type == "DNI"]
    assert len(dni) == 1
    assert dni[0].text == "12345678Z"


def test_detect_email():
    """Email debe detectarse."""
    d = RegexDetector()
    ents = d.detect("email: juan@example.com")
    email = [e for e in ents if e.type == "EMAIL"]
    assert len(email) == 1
    assert email[0].text == "juan@example.com"


def test_detect_phone():
    """Teléfono español debe detectarse."""
    d = RegexDetector()
    ents = d.detect("teléfono 612345678")
    phone = [e for e in ents if e.type == "PHONE"]
    assert len(phone) >= 1


def test_detect_ip():
    """IP debe detectarse."""
    d = RegexDetector()
    ents = d.detect("servidor 192.168.1.1")
    ip = [e for e in ents if e.type == "IP"]
    assert len(ip) == 1
    assert ip[0].text == "192.168.1.1"


def test_detect_jwt():
    """JWT debe detectarse."""
    d = RegexDetector()
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3j3kZJ1A_1g"
    ents = d.detect(f"token: {jwt}")
    tokens = [e for e in ents if e.type == "JWT"]
    assert len(tokens) >= 1


def test_no_false_positive_clinical_text():
    """Texto clínico normal no debe disparar falsos positivos masivos."""
    d = RegexDetector()
    text = (
        "El paciente presenta diabetes mellitus tipo 2. "
        "Se pauta metformina 850mg cada 12 horas. "
        "Ingresó el 12.05.2024 por insuficiencia cardíaca."
    )
    ents = d.detect(text)
    # La fecha 12.05.2024 debe detectarse como DATE no como IP
    # Buscar entidades que no sean DATE
    non_dates = [e for e in ents if e.type not in ("DATE",)]
    # No debería haber IPs ni DNIs en texto clínico normal
    assert all(e.type == "DATE" for e in ents)


def test_detect_nass():
    """NASS debe detectarse."""
    d = RegexDetector()
    ents = d.detect("NASS 12/12345678/12")
    nass = [e for e in ents if e.type == "NASS"]
    assert len(nass) >= 1
    assert "12/" in nass[0].text


def test_detect_multiple_in_one_text():
    """Varios tipos en un mismo texto."""
    d = RegexDetector()
    text = "Juan Pérez (DNI 12345678Z) email juan@mail.com tlf 612345678"
    ents = d.detect(text)
    types = {e.type for e in ents}
    assert "DNI" in types
    assert "EMAIL" in types
    assert "PHONE" in types