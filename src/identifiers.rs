// Copyright (c) 2026 Glomancy
// SPDX-License-Identifier: MIT

#[must_use]
pub fn is_uuid(value: &str) -> bool {
    if value.len() != 36 {
        return false;
    }
    for (index, byte) in value.bytes().enumerate() {
        if matches!(index, 8 | 13 | 18 | 23) {
            if byte != b'-' {
                return false;
            }
        } else if !byte.is_ascii_hexdigit() {
            return false;
        }
    }
    true
}

#[must_use]
pub fn is_lower_hex(value: &str, expected_len: usize) -> bool {
    value.len() == expected_len
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || matches!(byte, b'a'..=b'f'))
}

#[must_use]
pub fn is_sha256(value: &str) -> bool {
    is_lower_hex(value, 64)
}

#[must_use]
pub fn is_schema_urn(value: &str) -> bool {
    value.starts_with("urn:glomancy:protocol:")
        && !value.bytes().any(|byte| byte.is_ascii_whitespace())
        && value.matches(':').count() >= 4
}

#[must_use]
pub fn is_rfc3339_utc_shape(value: &str) -> bool {
    value.len() >= 20
        && value.ends_with('Z')
        && value.as_bytes().get(4) == Some(&b'-')
        && value.as_bytes().get(7) == Some(&b'-')
        && value.as_bytes().get(10) == Some(&b'T')
        && value.as_bytes().get(13) == Some(&b':')
        && value.as_bytes().get(16) == Some(&b':')
}
