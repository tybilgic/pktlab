#ifndef PKTLAB_DPDKD_PARSER_H
#define PKTLAB_DPDKD_PARSER_H

#include "pktlab_dpdkd/types.h"

struct rte_mbuf;

int pktlab_parser_parse(const struct rte_mbuf *packet, struct pkt_meta *meta);

#endif /* PKTLAB_DPDKD_PARSER_H */
