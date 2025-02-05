import sys
import logging
from scapy.all import *
import pandas as pd
from tabulate import tabulate
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def read_pcap(pcap_file):
    try:
        packets = rdpcap(pcap_file)
    except FileNotFoundError:
        logger.error(f"PCAP file not found: {pcap_file}")
        sys.exit(1)
    except Scapy_Exception as e:
        logger.error(f"Error reading PCAP file: {e}")
        sys.exit(1)
    return packets

def extract_packet_data(packets):
    packet_data = []

    for packet in tqdm(packets, desc="Processing packets", unit="packet"):
        if IP in packet:
            src_ip = packet[IP].src
            dst_ip = packet[IP].dst
            protocol = packet[IP].proto
            size = len(packet)
            packet_data.append({"src_ip": src_ip, "dst_ip": dst_ip, "protocol": protocol, "size": size})

    return pd.DataFrame(packet_data)

def protocol_name(number):
    protocol_dict = {1: 'ICMP', 6: 'TCP', 17: 'UDP'}
    return protocol_dict.get(number, f"Unknown({number})")

def analyze_packet_data(df):
    total_bandwidth = df["size"].sum()
    protocol_counts = df["protocol"].value_counts(normalize=True) * 100
    protocol_counts.index = protocol_counts.index.map(protocol_name)

    ip_communication = df.groupby(["src_ip", "dst_ip"]).size().sort_values(ascending=False)
    ip_communication_percentage = ip_communication / ip_communication.sum() * 100
    ip_communication_table = pd.concat([ip_communication, ip_communication_percentage], axis=1).reset_index()

    protocol_frequency = df["protocol"].value_counts()
    protocol_frequency.index = protocol_frequency.index.map(protocol_name)

    protocol_counts_df = pd.concat([protocol_frequency, protocol_counts], axis=1).reset_index()
    protocol_counts_df.columns = ["Protocol", "Count", "Percentage"]

    ip_communication_protocols = df.groupby(["src_ip", "dst_ip", "protocol"]).size().reset_index()
    ip_communication_protocols.columns = ["Source IP", "Destination IP", "Protocol", "Count"]
    ip_communication_protocols["Protocol"] = ip_communication_protocols["Protocol"].apply(protocol_name)

    # Fix: Use transform instead of apply
    ip_communication_protocols["Percentage"] = (
        ip_communication_protocols.groupby(["Source IP", "Destination IP"])["Count"]
        .transform(lambda x: x / x.sum() * 100)
    )

    return total_bandwidth, protocol_counts_df, ip_communication_table, protocol_frequency, ip_communication_protocols

def extract_packet_data_security(packets):
    packet_data = []

    for packet in tqdm(packets, desc="Processing packets for port scanning activity", unit="packet"):
        if IP in packet:
            src_ip = packet[IP].src
            dst_ip = packet[IP].dst
            protocol = packet[IP].proto
            size = len(packet)

            if TCP in packet:
                dst_port = packet[TCP].dport
            else:
                dst_port = 0

            packet_data.append({"src_ip": src_ip, "dst_ip": dst_ip, "protocol": protocol, "size": size, "dst_port": dst_port})

    return pd.DataFrame(packet_data)

def detect_port_scanning(df, port_scan_threshold):
    # Group packets by source IP and destination port
    port_scan_df = df.groupby(['src_ip', 'dst_port']).size().reset_index(name='count')
    
    # Count the unique ports for each source IP
    unique_ports_per_ip = port_scan_df.groupby('src_ip').size().reset_index(name='unique_ports')
    
    # Check for a large number of packets to different ports on a single IP address
    potential_port_scanners = unique_ports_per_ip[unique_ports_per_ip['unique_ports'] >= port_scan_threshold]
    ip_addresses = potential_port_scanners['src_ip'].unique()
    
    if len(ip_addresses) > 0:
        logger.warning(f"Potential port scanning detected from IP addresses: {', '.join(ip_addresses)}")

def print_results(total_bandwidth, protocol_counts_df, ip_communication_table, protocol_frequency, ip_communication_protocols):
    # Convert bandwidth to Mbps or Gbps
    if total_bandwidth < 10**9:
        bandwidth_unit = "Mbps"
        total_bandwidth /= 10**6
    else:
        bandwidth_unit = "Gbps"
        total_bandwidth /= 10**9

    logger.info(f"Total bandwidth used: {total_bandwidth:.2f} {bandwidth_unit}")
    logger.info("\nProtocol Distribution:\n")
    logger.info(tabulate(protocol_counts_df, headers=["Protocol", "Count", "Percentage"], tablefmt="grid"))
    logger.info("\nTop IP Address Communications:\n")
    logger.info(tabulate(ip_communication_table, headers=["Source IP", "Destination IP", "Count", "Percentage"], tablefmt="grid", floatfmt=".2f"))

    logger.info("\nShare of each protocol between IPs:\n")
    logger.info(tabulate(ip_communication_protocols, headers=["Source IP", "Destination IP", "Protocol", "Count", "Percentage"], tablefmt="grid", floatfmt=".2f"))

def plot_all_graphs(protocol_counts, ip_communication_protocols):
    plot_protocol_distribution(protocol_counts)
    plot_share_of_protocols_between_ips(ip_communication_protocols)

def plot_protocol_distribution(protocol_counts):
    plt.figure(figsize=(10, 6))
    protocol_counts.plot(kind='bar', x='Protocol', y='Count', legend=False)
    plt.title("Protocol Distribution")
    plt.xlabel("Protocol")
    plt.ylabel("Count")
    plt.show()

def plot_share_of_protocols_between_ips(ip_communication_protocols):
    plt.figure(figsize=(12, 8))
    for protocol, group in ip_communication_protocols.groupby('Protocol'):
        plt.scatter(group['Source IP'], group['Percentage'], label=protocol)
    plt.title("Share of Protocols Between IPs")
    plt.xlabel("Source IP")
    plt.ylabel("Percentage")
    plt.legend()
    plt.show()

def main(pcap_file, port_scan_threshold):
    packets = read_pcap(pcap_file)
    df = extract_packet_data(packets)
    total_bandwidth, protocol_counts, ip_communication_table, protocol_frequency, ip_communication_protocols = analyze_packet_data(df)
    print_results(total_bandwidth, protocol_counts, ip_communication_table, protocol_frequency, ip_communication_protocols)
    df = extract_packet_data_security(packets)
    detect_port_scanning(df, port_scan_threshold)
    plot_all_graphs(protocol_counts, ip_communication_protocols)

if __name__ == "__main__":
    # Hardcoded file path and port scan threshold
    pcap_file = "/Users/neha/network1.pcapng"  # Update this path to your .pcapng file
    port_scan_threshold = 100  # Set your desired threshold

    # Run the main function
    main(pcap_file, port_scan_threshold)
    

#change with seaborn
def plot_protocol_distribution(protocol_counts_df):
    plt.figure(figsize=(10, 6))
    
    # Sort by count for better visualization
    protocol_counts_df = protocol_counts_df.sort_values(by="Count", ascending=False)
    
    # Create the bar plot
    ax = sns.barplot(data=protocol_counts_df, x="Protocol", y="Count", palette="viridis")

    # Add value labels
    for p in ax.patches:
        ax.annotate(f'{int(p.get_height())}', 
                    (p.get_x() + p.get_width() / 2., p.get_height()), 
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Improve aesthetics
    plt.title("Protocol Distribution", fontsize=14, fontweight="bold")
    plt.xlabel("Protocol", fontsize=12)
    plt.ylabel("Count", fontsize=12)
    sns.despine()  # Remove borders for a cleaner look

    # Show the plot
    plt.show()
