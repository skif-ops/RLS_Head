#include "evt_gnss_parser.h"

#include <stdlib.h>
#include <string.h>

static int hex_value(char c)
{
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    return -1;
}

static int64_t days_from_civil(int year, unsigned month, unsigned day)
{
    year -= month <= 2u;
    const int era = (year >= 0 ? year : year - 399) / 400;
    const unsigned yoe = (unsigned)(year - era * 400);
    const unsigned adjusted_month = month > 2u ? month - 3u : month + 9u;
    const unsigned doy = (153u * adjusted_month + 2u) / 5u + day - 1u;
    const unsigned doe = yoe * 365u + yoe / 4u - yoe / 100u + doy;
    return (int64_t)era * 146097 + (int64_t)doe - 719468;
}

static bool parse_two_digits(const char *p, unsigned *value)
{
    if (p[0] < '0' || p[0] > '9' || p[1] < '0' || p[1] > '9') {
        return false;
    }
    *value = (unsigned)(p[0] - '0') * 10u + (unsigned)(p[1] - '0');
    return true;
}

static bool parse_rmc_time(
    const char *time_field,
    const char *date_field,
    uint64_t *reference_time_us)
{
    if (strlen(time_field) < 6u || strlen(date_field) != 6u) {
        return false;
    }

    unsigned hour;
    unsigned minute;
    unsigned second;
    unsigned day;
    unsigned month;
    unsigned year2;
    if (!parse_two_digits(&time_field[0], &hour)
        || !parse_two_digits(&time_field[2], &minute)
        || !parse_two_digits(&time_field[4], &second)
        || !parse_two_digits(&date_field[0], &day)
        || !parse_two_digits(&date_field[2], &month)
        || !parse_two_digits(&date_field[4], &year2)
        || hour > 23u
        || minute > 59u
        || second > 60u
        || day == 0u
        || day > 31u
        || month == 0u
        || month > 12u) {
        return false;
    }

    unsigned fractional_us = 0u;
    const char *dot = strchr(time_field, '.');
    if (dot != NULL) {
        unsigned scale = 100000u;
        for (const char *p = dot + 1; *p >= '0' && *p <= '9' && scale > 0u; ++p) {
            fractional_us += (unsigned)(*p - '0') * scale;
            scale /= 10u;
        }
    }

    const int year = (year2 >= 80u ? 1900 : 2000) + (int)year2;
    const int64_t days = days_from_civil(year, month, day);
    if (days < 0) {
        return false;
    }

    const uint64_t seconds = (uint64_t)days * 86400u
        + (uint64_t)hour * 3600u
        + (uint64_t)minute * 60u
        + second;
    *reference_time_us = seconds * 1000000u + fractional_us;
    return true;
}

static void parse_sentence(evt_gnss_parser_t *parser)
{
    char *star = strchr(parser->line, '*');
    if (parser->line[0] != '$' || star == NULL || strlen(star) != 3u) {
        parser->checksum_errors++;
        return;
    }

    uint8_t checksum = 0u;
    for (char *p = &parser->line[1]; p < star; ++p) {
        checksum ^= (uint8_t)*p;
    }
    const int high = hex_value(star[1]);
    const int low = hex_value(star[2]);
    if (high < 0 || low < 0 || checksum != (uint8_t)((high << 4) | low)) {
        parser->checksum_errors++;
        return;
    }

    *star = '\0';
    char *fields[16] = {0};
    size_t count = 0u;
    for (char *field = parser->line; field != NULL && count < 16u;) {
        fields[count++] = field;
        char *comma = strchr(field, ',');
        if (comma == NULL) {
            break;
        }
        *comma = '\0';
        field = comma + 1;
    }

    parser->valid_sentences++;
    const size_t type_length = strlen(fields[0]);
    const char *type = type_length >= 3u ? fields[0] + type_length - 3u : "";
    if (strcmp(type, "GGA") == 0 && count > 6u) {
        parser->fix_valid = fields[6][0] >= '1' && fields[6][0] <= '8';
    } else if (strcmp(type, "RMC") == 0 && count > 9u) {
        parser->fix_valid = fields[2][0] == 'A';
        parser->time_valid = parser->fix_valid
            && parse_rmc_time(fields[1], fields[9], &parser->reference_time_us);
        parser->have_reference_time = parser->time_valid;
    }
}

void evt_gnss_parser_init(evt_gnss_parser_t *parser)
{
    if (parser != NULL) {
        memset(parser, 0, sizeof(*parser));
    }
}

void evt_gnss_parser_feed(
    evt_gnss_parser_t *parser,
    const uint8_t *data,
    size_t length)
{
    if (parser == NULL || (data == NULL && length != 0u)) {
        return;
    }

    for (size_t i = 0u; i < length; ++i) {
        const char c = (char)data[i];
        if (c == '$') {
            parser->length = 0u;
        }
        if (parser->length == 0u && c != '$') {
            continue;
        }
        if (c == '\r') {
            continue;
        }
        if (c == '\n') {
            parser->line[parser->length] = '\0';
            parse_sentence(parser);
            parser->length = 0u;
            continue;
        }
        if (parser->length + 1u >= sizeof(parser->line)) {
            parser->length = 0u;
            continue;
        }
        parser->line[parser->length++] = c;
    }
}
