# Task 1 - Custom MCP Server

## Overview

This project implements a custom Model Context Protocol (MCP) server using
the official Python MCP SDK.

The server communicates using STDIO transport and exposes two tools:

- `get_customer_record`
- `trigger_refund`

## Features

### get_customer_record

Accepts a customer ID using the format:

`CUST-XXXXX`

Example:

`CUST-12345`

### trigger_refund

Accepts:

- `customer_id` - must match `CUST-XXXXX`
- `amount` - must be greater than zero
- `reason` - minimum 10 characters

## Validation

Input validation is enforced using Pydantic constraints.

Invalid customer IDs, non-positive refund amounts, short refund reasons,
and unexpected fields are rejected.

## STDIO Transport

The MCP server communicates through STDIO.

stdout is reserved exclusively for MCP/JSON-RPC protocol communication.

Application and diagnostic logging is explicitly configured to use stderr
to prevent corruption of the MCP transport.

## Installation

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r requirements.txt