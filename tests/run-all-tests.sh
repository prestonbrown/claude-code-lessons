#!/bin/bash
# SPDX-License-Identifier: MIT
# run-all-tests.sh - Run all test suites

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "========================================"
echo "  Coding Agent Lessons - Test Runner"
echo "========================================"

failed=0

echo ""
echo -e "${YELLOW}Running lessons-manager tests...${NC}"
if ! "$SCRIPT_DIR/test-lessons-manager.sh"; then
    failed=1
fi

echo ""
echo -e "${YELLOW}Running install script tests...${NC}"
if ! "$SCRIPT_DIR/test-install.sh"; then
    failed=1
fi

echo ""
echo "========================================"
if [[ $failed -eq 0 ]]; then
    echo -e "${GREEN}All test suites passed!${NC}"
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
