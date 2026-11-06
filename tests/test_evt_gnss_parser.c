#include "evt_gnss_parser.h"

#include <stdint.h>
#include <string.h>

static int accepts_valid_rmc(void)
{
    static const char sentence[] =
        "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n";
    evt_gnss_parser_t parser;
    evt_gnss_parser_init(&parser);
    evt_gnss_parser_feed(&parser, (const uint8_t *)sentence, strlen(sentence));
    return parser.valid_sentences == 1u
        && parser.checksum_errors == 0u
        && parser.fix_valid
        && parser.time_valid
        && parser.have_reference_time
        && parser.reference_time_us == UINT64_C(764426119000000)
        ? 0 : 1;
}

static int rejects_bad_checksum(void)
{
    static const char sentence[] =
        "$GPRMC,123519,V,,,,,,,230394,,,N*00\r\n";
    evt_gnss_parser_t parser;
    evt_gnss_parser_init(&parser);
    evt_gnss_parser_feed(&parser, (const uint8_t *)sentence, strlen(sentence));
    return parser.valid_sentences == 0u && parser.checksum_errors == 1u ? 0 : 1;
}

int main(void)
{
    if (accepts_valid_rmc() != 0) {
        return 1;
    }
    return rejects_bad_checksum() == 0 ? 0 : 2;
}
