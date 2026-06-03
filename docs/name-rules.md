# Preset Name Rules

Preset names are written through Fuji property `0xD18D` as PTP strings.

This is separate from generic PTP string capacity. The camera accepts a much narrower practical
name format for custom recipe names.

## Observed Rules

| Rule | Value |
|---|---|
| Maximum length | 25 characters |
| Encoding | PTP string, UTF-16LE with length byte and null terminator |
| Letters | `A-Z`, `a-z` |
| Digits | `0-9` |
| Space | allowed |
| Punctuation | limited ASCII punctuation, listed below |

Allowed punctuation:

```text
! " # $ % & ' ( ) * + , - . / : ; < = > ? @ [ ] \ ^ _ { } | ~
```

## Normalization Recommendations

Before writing:

1. Normalize text to NFD.
2. Remove combining marks so accented letters fold to ASCII.
3. Convert smart apostrophes to straight apostrophe `'`.
4. Replace unsupported characters with spaces.
5. Collapse repeated spaces.
6. Trim leading and trailing spaces.
7. Truncate to 25 characters.
8. Trim trailing spaces again.
9. If empty, use a fallback such as `Untitled` or the slot label.

## Known Character Gotchas

The camera UI may render or expose characters differently than PTP writes accept.

- ASCII `-` may render on the camera like a longer dash. Write ASCII `-`.
- Do not write Unicode en dash, em dash, horizontal bar, or middle dot unless a body-specific
  test proves they work.
- Emoji and symbols outside the safe set should be stripped or converted to spaces.

## Known Length Gotcha

The on-camera name entry appears capped at 25 characters. Use 25 as the protocol-safe maximum.

## Example

Input:

```text
Cafe with accent, smart apostrophe, emoji
```

Output behavior:

```text
accent folded
smart apostrophe converted to '
emoji removed or collapsed to space
result truncated to 25 characters
```

## PTP String Example

For name `C1`:

```text
03 43 00 31 00 00 00
```

Explanation:

- `03`: character count including null terminator
- `43 00`: `C`
- `31 00`: `1`
- `00 00`: null terminator
