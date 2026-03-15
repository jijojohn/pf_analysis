#!/bin/bash
# =============================================================================
# Portfolio Analysis System - Complete Runner Script
# Architecture: Separate Data Fetching from Analysis
#
# IMPORTANT: Always use this script to run the system. Do NOT run Python
# files directly — this script manages the virtual environment, data
# freshness checks, and proper execution order.
#
# Usage:
#   ./run.sh                  Full pipeline (default): verify → fetch → generate reports
#   ./run.sh --full           Same as above (explicit)
#   ./run.sh --reports-only   Skip data fetch, regenerate reports with cached data
#   ./run.sh --update-only    Only fetch/update data, skip report generation
#   ./run.sh --serve [PORT]   Start local web server to view reports (default: 8080)
#   ./run.sh --clean          Delete all reports and regenerate from scratch
#   ./run.sh --help           Show this help message
#
# Virtual Environment:
#   This script ALWAYS uses the local ./venv virtual environment.
#   If venv does not exist, it will be created and dependencies installed.
#   NEVER run python files directly outside of venv.
# =============================================================================

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}===============================================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${BLUE}===============================================================================${NC}"
}

print_step() {
    echo -e "${GREEN}🔄 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${CYAN}💡 $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# =============================================================================
# Help / Usage
# =============================================================================
show_help() {
    echo -e "${BOLD}Portfolio Analysis System — Runner Script${NC}"
    echo ""
    echo -e "${CYAN}Usage:${NC}"
    echo "  ./run.sh [OPTION]"
    echo ""
    echo -e "${CYAN}Options:${NC}"
    echo "  (none), --full      Full pipeline: verify data → fetch updates → generate reports"
    echo "  --reports-only      Skip data fetch, regenerate reports using cached data"
    echo "  --update-only       Only fetch/update portfolio & benchmark data"
    echo "  --serve [PORT]      Start a local HTTP server to browse reports (default port: 8080)"
    echo "  --clean             Delete all reports and run the full pipeline from scratch"
    echo "  --help, -h          Show this help message"
    echo ""
    echo -e "${CYAN}Examples:${NC}"
    echo "  ./run.sh                    # Full pipeline (most common)"
    echo "  ./run.sh --reports-only     # Re-generate reports without fetching data"
    echo "  ./run.sh --serve            # Serve reports on http://localhost:8080"
    echo "  ./run.sh --serve 9000       # Serve reports on http://localhost:9000"
    echo "  ./run.sh --clean            # Fresh start — delete old reports and regenerate"
    echo ""
    echo -e "${CYAN}Virtual Environment:${NC}"
    echo "  This script ALWAYS activates ./venv before running any Python code."
    echo "  If ./venv does not exist, it will be auto-created with all dependencies."
    echo "  Do NOT run Python files directly — always use this script."
    echo ""
    exit 0
}

# =============================================================================
# Parse Arguments
# =============================================================================
MODE="full"
SERVE_PORT=8080

while [[ $# -gt 0 ]]; do
    case "$1" in
        --full)
            MODE="full"
            shift
            ;;
        --reports-only)
            MODE="reports-only"
            shift
            ;;
        --update-only)
            MODE="update-only"
            shift
            ;;
        --serve)
            MODE="serve"
            shift
            # Check if next argument is a port number
            if [[ $# -gt 0 && "$1" =~ ^[0-9]+$ ]]; then
                SERVE_PORT="$1"
                shift
            fi
            ;;
        --clean)
            MODE="clean"
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# Start time
start_time=$(date +%s)

print_header "🚀 PORTFOLIO ANALYSIS SYSTEM"
echo ""
echo -e "${CYAN}Mode: ${BOLD}${MODE}${NC}"
echo ""

# =============================================================================
# Environment Setup (always runs)
# =============================================================================
setup_venv() {
    print_step "Setting up virtual environment..."

    if [ ! -d "venv" ]; then
        print_warning "Virtual environment not found. Creating it..."
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            print_error "Failed to create virtual environment"
            exit 1
        fi
        source venv/bin/activate
        print_step "Installing requirements..."
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            print_error "Failed to install requirements"
            exit 1
        fi
    else
        source venv/bin/activate
    fi

    # Use venv Python for all subsequent commands
    PYTHON="venv/bin/python3"

    print_success "Virtual environment active ($(python3 --version))"
}

# =============================================================================
# Check portfolio file (needed for data + report modes)
# =============================================================================
check_portfolio_file() {
    if [ ! -f "dpsr_report.xls.xlsx" ]; then
        print_error "Portfolio file dpsr_report.xls.xlsx not found!"
        exit 1
    fi
    print_success "Portfolio file found"
}

# =============================================================================
# STEP: VERIFY & FETCH DATA
# =============================================================================
run_data_update() {
    print_header "🔍 VERIFY DATA FRESHNESS"

    print_step "Checking if cached data is up-to-date..."
    set +e
    $PYTHON verify_data_freshness.py -p
    freshness_status=$?
    set -e

    if [ $freshness_status -eq 0 ]; then
        print_success "Cached data is fresh and up-to-date"
        print_info "Skipping data update — using cached data"
        data_update_status=0
        benchmark_status=0
    else
        print_info "Stale or missing data detected — proceeding with delta update"

        print_header "📡 DATA UPDATE (DELTA FETCH)"

        print_step "Updating portfolio data (incremental delta fetch)..."
        set +e
        $PYTHON update_portfolio_data.py
        data_update_status=$?
        set -e

        if [ $data_update_status -ne 0 ]; then
            print_error "Data update failed, but continuing with cached data..."
        else
            print_success "Portfolio data updated successfully"
        fi

        # Update benchmarks and indices
        print_step "Updating benchmarks and indices..."
        set +e
        $PYTHON update_portfolio_data.py --benchmarks
        benchmark_status=$?
        set -e

        if [ $benchmark_status -eq 0 ]; then
            print_success "Benchmarks updated successfully"
        else
            print_info "Benchmark update completed with warnings"
        fi
    fi
}

# =============================================================================
# STEP: PREPARE REPORTS DIRECTORY
# =============================================================================
prepare_reports_dir() {
    print_header "🧹 PREPARE REPORTS DIRECTORY"

    print_step "Preparing reports directory..."
    if [ -d "reports" ]; then
        print_info "Reports directory exists — old reports will be auto-cleaned by the app (retention: 1 day)"
        print_success "Reports directory ready"
    else
        mkdir -p reports
        print_success "Reports directory created"
    fi
}

# =============================================================================
# STEP: GENERATE REPORTS
# =============================================================================
run_report_generation() {
    print_header "📊 TECHNICAL ANALYSIS & REPORTS"

    print_step "Generating technical indicators and comprehensive reports..."
    print_info "This includes: Technical indicators, Risk metrics, Portfolio optimization, Filtered reports"
    echo ""
    set +e
    $PYTHON main_pf_app.py
    analysis_status=$?
    set -e

    if [ $analysis_status -eq 0 ]; then
        print_success "Technical analysis and report generation completed successfully"
    else
        print_error "Analysis encountered some errors (exit code: $analysis_status)"
    fi
}

# =============================================================================
# STEP: SERVE REPORTS (Web Server)
# =============================================================================
run_serve() {
    if [ ! -d "reports" ] || [ -z "$(ls -A reports/ 2>/dev/null)" ]; then
        print_error "No reports found in reports/ directory."
        print_info "Run './run.sh' first to generate reports, then './run.sh --serve' to view them."
        exit 1
    fi

    print_header "🌐 SERVING REPORTS"
    echo ""
    print_success "Starting local web server..."
    echo ""
    echo -e "${CYAN}  Open in browser: ${BOLD}http://localhost:${SERVE_PORT}/reports/index.html${NC}"
    echo ""
    print_info "Press Ctrl+C to stop the server"
    echo ""

    $PYTHON -m http.server "$SERVE_PORT"
}

# =============================================================================
# Summary
# =============================================================================
print_summary() {
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    minutes=$((duration / 60))
    seconds=$((duration % 60))

    print_header "📋 EXECUTION SUMMARY"
    echo ""
    echo -e "${CYAN}⏱️  Total Time: ${minutes}m ${seconds}s${NC}"
    echo -e "${CYAN}📌 Mode: ${MODE}${NC}"
    echo ""

    if [ "${analysis_status:-0}" -eq 0 ]; then
        echo -e "${GREEN}✅ PORTFOLIO ANALYSIS COMPLETED SUCCESSFULLY${NC}"
        echo ""
        echo -e "${CYAN}📁 Generated Files:${NC}"
        current_date=$(date +%Y%m%d)
        echo "   📊 reports/index.html"
        echo "   📄 reports/portfolio_report_${current_date}.html"
        echo "   📈 reports/comprehensive_dataset_${current_date}.csv"
        echo "   🏥 reports/portfolio_health_${current_date}.html"
        echo "   🚨 reports/alert_conditions_${current_date}.html"
        echo "   📈 reports/performance_trend_${current_date}.html"
        echo "   📋 reports/filtered_report_*.html (multiple)"
        echo ""
        echo -e "${CYAN}💡 Next Steps:${NC}"
        echo "   1. Open reports/index.html in your browser"
        echo "   2. Or run: ./run.sh --serve"
        echo ""
    else
        echo -e "${YELLOW}⚠️  PORTFOLIO ANALYSIS COMPLETED WITH SOME ISSUES${NC}"
        echo ""
        echo -e "${CYAN}💡 Troubleshooting:${NC}"
        echo "   - Check if all symbols have cached data"
        echo "   - Run: ./run.sh --update-only"
        echo "   - Review error messages above"
        echo ""
    fi

    print_header "🎯 RUN COMPLETE"
}

# =============================================================================
# MAIN — Execute based on selected mode
# =============================================================================

# Always set up venv first
setup_venv

case "$MODE" in
    full)
        print_info "Running full pipeline: verify → fetch → generate reports"
        echo ""
        check_portfolio_file
        run_data_update
        prepare_reports_dir
        run_report_generation
        print_summary
        ;;
    reports-only)
        print_info "Regenerating reports with cached data (skipping data fetch)"
        echo ""
        check_portfolio_file
        prepare_reports_dir
        run_report_generation
        print_summary
        ;;
    update-only)
        print_info "Updating data only (no report generation)"
        echo ""
        check_portfolio_file
        run_data_update
        echo ""
        print_success "Data update complete. Run './run.sh --reports-only' to generate reports."
        ;;
    clean)
        print_info "Clean run: deleting old reports and regenerating from scratch"
        echo ""
        check_portfolio_file
        if [ -d "reports" ]; then
            print_step "Removing old reports..."
            rm -rf reports/*
            print_success "Reports directory cleaned"
        fi
        run_data_update
        prepare_reports_dir
        run_report_generation
        print_summary
        ;;
    serve)
        run_serve
        ;;
esac
