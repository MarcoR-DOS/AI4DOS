#include <string.h>
#include "sha256.h"

typedef struct {
    uint32_t h[8];
    uint32_t total_lo;
    uint32_t total_hi;
    unsigned used;
    unsigned char block[64];
} Sha256Ctx;

static const uint32_t k[64] = {
    0x428a2f98UL,0x71374491UL,0xb5c0fbcfUL,0xe9b5dba5UL,
    0x3956c25bUL,0x59f111f1UL,0x923f82a4UL,0xab1c5ed5UL,
    0xd807aa98UL,0x12835b01UL,0x243185beUL,0x550c7dc3UL,
    0x72be5d74UL,0x80deb1feUL,0x9bdc06a7UL,0xc19bf174UL,
    0xe49b69c1UL,0xefbe4786UL,0x0fc19dc6UL,0x240ca1ccUL,
    0x2de92c6fUL,0x4a7484aaUL,0x5cb0a9dcUL,0x76f988daUL,
    0x983e5152UL,0xa831c66dUL,0xb00327c8UL,0xbf597fc7UL,
    0xc6e00bf3UL,0xd5a79147UL,0x06ca6351UL,0x14292967UL,
    0x27b70a85UL,0x2e1b2138UL,0x4d2c6dfcUL,0x53380d13UL,
    0x650a7354UL,0x766a0abbUL,0x81c2c92eUL,0x92722c85UL,
    0xa2bfe8a1UL,0xa81a664bUL,0xc24b8b70UL,0xc76c51a3UL,
    0xd192e819UL,0xd6990624UL,0xf40e3585UL,0x106aa070UL,
    0x19a4c116UL,0x1e376c08UL,0x2748774cUL,0x34b0bcb5UL,
    0x391c0cb3UL,0x4ed8aa4aUL,0x5b9cca4fUL,0x682e6ff3UL,
    0x748f82eeUL,0x78a5636fUL,0x84c87814UL,0x8cc70208UL,
    0x90befffaUL,0xa4506cebUL,0xbef9a3f7UL,0xc67178f2UL
};

#define ROR(x,n) (((x) >> (n)) | ((x) << (32-(n))))
#define CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define BS0(x) (ROR((x),2) ^ ROR((x),13) ^ ROR((x),22))
#define BS1(x) (ROR((x),6) ^ ROR((x),11) ^ ROR((x),25))
#define SS0(x) (ROR((x),7) ^ ROR((x),18) ^ ((x) >> 3))
#define SS1(x) (ROR((x),17) ^ ROR((x),19) ^ ((x) >> 10))

static void transform(Sha256Ctx *ctx, const unsigned char *b)
{
    uint32_t w[64];
    uint32_t a,c,d,e,f,g,h,t1,t2;
    uint32_t bb;
    unsigned i;

    for (i = 0; i < 16; ++i) {
        w[i] = ((uint32_t)b[i*4] << 24) |
               ((uint32_t)b[i*4+1] << 16) |
               ((uint32_t)b[i*4+2] << 8) | b[i*4+3];
    }
    for (i = 16; i < 64; ++i)
        w[i] = SS1(w[i-2]) + w[i-7] + SS0(w[i-15]) + w[i-16];
    a=ctx->h[0]; bb=ctx->h[1]; c=ctx->h[2]; d=ctx->h[3];
    e=ctx->h[4]; f=ctx->h[5]; g=ctx->h[6]; h=ctx->h[7];
    for (i = 0; i < 64; ++i) {
        t1 = h + BS1(e) + CH(e,f,g) + k[i] + w[i];
        t2 = BS0(a) + MAJ(a,bb,c);
        h=g; g=f; f=e; e=d+t1; d=c; c=bb; bb=a; a=t1+t2;
    }
    ctx->h[0]+=a; ctx->h[1]+=bb; ctx->h[2]+=c; ctx->h[3]+=d;
    ctx->h[4]+=e; ctx->h[5]+=f; ctx->h[6]+=g; ctx->h[7]+=h;
}

static void init(Sha256Ctx *ctx)
{
    ctx->h[0]=0x6a09e667UL; ctx->h[1]=0xbb67ae85UL;
    ctx->h[2]=0x3c6ef372UL; ctx->h[3]=0xa54ff53aUL;
    ctx->h[4]=0x510e527fUL; ctx->h[5]=0x9b05688cUL;
    ctx->h[6]=0x1f83d9abUL; ctx->h[7]=0x5be0cd19UL;
    ctx->total_lo=0; ctx->total_hi=0; ctx->used=0;
}

static void update(Sha256Ctx *ctx, const unsigned char *data, size_t len)
{
    uint32_t old;
    size_t take;

    old = ctx->total_lo;
    ctx->total_lo += (uint32_t)len;
    if (ctx->total_lo < old) ++ctx->total_hi;
    while (len != 0) {
        take = 64 - ctx->used;
        if (take > len) take = len;
        memcpy(ctx->block + ctx->used, data, take);
        ctx->used += (unsigned)take;
        data += take;
        len -= take;
        if (ctx->used == 64) {
            transform(ctx, ctx->block);
            ctx->used = 0;
        }
    }
}

static void finish(Sha256Ctx *ctx, unsigned char digest[32])
{
    uint32_t bit_hi, bit_lo;
    unsigned i;

    bit_hi = (ctx->total_hi << 3) | (ctx->total_lo >> 29);
    bit_lo = ctx->total_lo << 3;
    ctx->block[ctx->used++] = 0x80;
    if (ctx->used > 56) {
        while (ctx->used < 64) ctx->block[ctx->used++] = 0;
        transform(ctx, ctx->block);
        ctx->used = 0;
    }
    while (ctx->used < 56) ctx->block[ctx->used++] = 0;
    for (i = 0; i < 4; ++i) {
        ctx->block[56+i] = (unsigned char)(bit_hi >> (24-i*8));
        ctx->block[60+i] = (unsigned char)(bit_lo >> (24-i*8));
    }
    transform(ctx, ctx->block);
    for (i = 0; i < 8; ++i) {
        digest[i*4]   = (unsigned char)(ctx->h[i] >> 24);
        digest[i*4+1] = (unsigned char)(ctx->h[i] >> 16);
        digest[i*4+2] = (unsigned char)(ctx->h[i] >> 8);
        digest[i*4+3] = (unsigned char)ctx->h[i];
    }
}

void sha256_digest(const unsigned char *data, size_t len,
                   unsigned char digest[32])
{
    Sha256Ctx ctx;
    init(&ctx);
    update(&ctx, data, len);
    finish(&ctx, digest);
}

void hmac_sha256(const unsigned char *key, size_t key_len,
                 const unsigned char *data, size_t data_len,
                 unsigned char digest[32])
{
    Sha256Ctx ctx;
    unsigned char key_block[64];
    unsigned char inner[32];
    unsigned char pad[64];
    unsigned i;

    memset(key_block, 0, sizeof(key_block));
    if (key_len > 64) sha256_digest(key, key_len, key_block);
    else memcpy(key_block, key, key_len);
    for (i = 0; i < 64; ++i) pad[i] = key_block[i] ^ 0x36;
    init(&ctx); update(&ctx, pad, 64); update(&ctx, data, data_len);
    finish(&ctx, inner);
    for (i = 0; i < 64; ++i) pad[i] = key_block[i] ^ 0x5c;
    init(&ctx); update(&ctx, pad, 64); update(&ctx, inner, 32);
    finish(&ctx, digest);
    memset(key_block, 0, sizeof(key_block));
    memset(inner, 0, sizeof(inner));
}

void digest_to_hex(const unsigned char digest[32], char hex[65])
{
    static const char digits[] = "0123456789abcdef";
    unsigned i;
    for (i = 0; i < 32; ++i) {
        hex[i*2] = digits[digest[i] >> 4];
        hex[i*2+1] = digits[digest[i] & 15];
    }
    hex[64] = 0;
}

