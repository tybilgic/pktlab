#include "parser.h"

#include <limits.h>
#include <stdint.h>
#include <string.h>

#if PKTLAB_DPDKD_HAS_DPDK
#include <rte_byteorder.h>
#include <rte_ether.h>
#include <rte_ip.h>
#include <rte_mbuf.h>
#include <rte_tcp.h>
#include <rte_udp.h>
#endif

int pktlab_parser_parse(const struct rte_mbuf *packet, struct pkt_meta *meta)
{
    memset(meta, 0, sizeof(*meta));

#if !PKTLAB_DPDKD_HAS_DPDK
    (void) packet;
    return -1;
#else
    const struct rte_ether_hdr *ether_header;
    struct rte_ether_hdr ether_header_copy;
    uint32_t packet_length;

    packet_length = rte_pktmbuf_pkt_len(packet);
    meta->pkt_len = (packet_length > UINT16_MAX) ? UINT16_MAX : (uint16_t) packet_length;

    ether_header = rte_pktmbuf_read(
        packet,
        0U,
        sizeof(ether_header_copy),
        &ether_header_copy
    );
    if (ether_header == NULL) {
        return -1;
    }

    meta->ether_type = rte_be_to_cpu_16(ether_header->ether_type);
    if (meta->ether_type != RTE_ETHER_TYPE_IPV4) {
        return 0;
    }

    {
        const uint32_t ip_offset = sizeof(struct rte_ether_hdr);
        const struct rte_ipv4_hdr *ipv4_header;
        struct rte_ipv4_hdr ipv4_header_copy;
        uint8_t version;
        uint8_t ihl_words;
        uint32_t l4_offset;

        ipv4_header = rte_pktmbuf_read(
            packet,
            ip_offset,
            sizeof(ipv4_header_copy),
            &ipv4_header_copy
        );
        if (ipv4_header == NULL) {
            return -1;
        }

        version = (uint8_t) (ipv4_header->version_ihl >> 4);
        ihl_words = (uint8_t) (ipv4_header->version_ihl & 0x0FU);
        if (version != 4U || ihl_words < 5U) {
            return -1;
        }

        meta->l4_proto = ipv4_header->next_proto_id;
        meta->src_ip = rte_be_to_cpu_32(ipv4_header->src_addr);
        meta->dst_ip = rte_be_to_cpu_32(ipv4_header->dst_addr);
        l4_offset = ip_offset + ((uint32_t) ihl_words * 4U);

        if (meta->l4_proto == IPPROTO_TCP) {
            const struct rte_tcp_hdr *tcp_header;
            struct rte_tcp_hdr tcp_header_copy;

            tcp_header = rte_pktmbuf_read(
                packet,
                l4_offset,
                sizeof(tcp_header_copy),
                &tcp_header_copy
            );
            if (tcp_header == NULL) {
                return -1;
            }

            meta->src_port = rte_be_to_cpu_16(tcp_header->src_port);
            meta->dst_port = rte_be_to_cpu_16(tcp_header->dst_port);
        } else if (meta->l4_proto == IPPROTO_UDP) {
            const struct rte_udp_hdr *udp_header;
            struct rte_udp_hdr udp_header_copy;

            udp_header = rte_pktmbuf_read(
                packet,
                l4_offset,
                sizeof(udp_header_copy),
                &udp_header_copy
            );
            if (udp_header == NULL) {
                return -1;
            }

            meta->src_port = rte_be_to_cpu_16(udp_header->src_port);
            meta->dst_port = rte_be_to_cpu_16(udp_header->dst_port);
        }
    }

    return 0;
#endif
}
