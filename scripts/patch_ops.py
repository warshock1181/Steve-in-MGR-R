"""Copy/literal patches: unchanged model data comes from the recipient's game."""
import base64
import hashlib
import json
import zlib


def sha256(blob):
    return hashlib.sha256(blob).hexdigest()


def apply_patch(original, packed):
    patch = json.loads(zlib.decompress(packed))
    if patch['format'] != 'block-raiden-copy-1' or sha256(original) != patch['source_sha256']:
        raise ValueError('Model version does not match this release')
    result = bytearray()
    for operation in patch['operations']:
        if operation[0] == 'copy':
            _, offset, size = operation
            if offset < 0 or size < 0 or offset + size > len(original):
                raise ValueError('Invalid patch reference')
            result.extend(original[offset:offset + size])
        elif operation[0] == 'data':
            result.extend(base64.b64decode(operation[1], validate=True))
        else:
            raise ValueError('Unknown patch operation')
        if len(result) > 64 * 1024 * 1024:
            raise ValueError('Patched model exceeds size limit')
    if len(result) != patch['target_size'] or sha256(result) != patch['target_sha256']:
        raise ValueError('Patched model verification failed')
    return bytes(result)
