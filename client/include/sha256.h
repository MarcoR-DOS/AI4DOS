#ifndef AI4DOS_SHA256_H
#define AI4DOS_SHA256_H

#include <stddef.h>
#include <stdint.h>

void sha256_digest(const unsigned char *data, size_t len,
                   unsigned char digest[32]);
void hmac_sha256(const unsigned char *key, size_t key_len,
                 const unsigned char *data, size_t data_len,
                 unsigned char digest[32]);
void digest_to_hex(const unsigned char digest[32], char hex[65]);

#endif

