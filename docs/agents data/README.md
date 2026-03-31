# Agent Training Data

Updated: March 2026

This directory contains scraped business listing data used for agent persona training and market intelligence.

## Files

| File | Rows | Description |
|------|------|-------------|
| `mixed.csv` | 85+ | Mixed business listings (real estate firms, legal consultants, CAs) |
| `property_consultant.csv` | 134+ | Property consultants and real estate agencies |
| `real_estate_broker.csv` | 128+ | Real estate brokers |
| `real_estate.csv` | 99+ | General real estate entities |

## Schema

All CSVs share a common schema with columns:
- Business name, rating, review count
- Address, city, Google Maps URL
- Phone, email, website
- Social media links (Facebook, Instagram, LinkedIn, Twitter)
- Additional metadata (hours, services, etc.)

## Usage

This data is used by:
- Agent persona initialization (broker, consultant profiles)
- Market intelligence for locality analysis
- Training data for business classification models

## Notes

- Data sourced from Google Maps public listings.
- Many entries have sparse data due to varying source availability.
- Data quality varies; use with appropriate filtering.
