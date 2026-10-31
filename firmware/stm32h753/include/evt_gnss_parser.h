#ifndef EVT_GNSS_PARSER_H
#define EVT_GNSS_PARSER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define EVT_NMEA_LINE_CAPACITY 128u

typedef struct {
    char line[EVT_NMEA_LINE_CAPACITY];
    size_t length;
    uint64_t reference_time_us;
    uint32_t valid_sentences;
    uint32_t checksum_errors;
    bool fix_valid;
    bool time_valid;
    bool have_reference_time;
} evt_gnss_parser_t;

void evt_gnss_parser_init(evt_gnss_parser_t *parser);

void evt_gnss_parser_feed(
    evt_gnss_parser_t *parser,
    const uint8_t *data,
    size_t length);

#endif
