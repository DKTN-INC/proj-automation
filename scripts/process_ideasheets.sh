#!/bin/bash
#
# Process Ideasheets Script
# This script processes markdown files in the ideasheets directory
# and converts them to HTML and PDF with enhanced features.
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
IDEASHEETS_DIR="${REPO_ROOT}/docs/ideasheets"
OUTPUT_DIR="${REPO_ROOT}/output"
TEMPLATES_DIR="${SCRIPT_DIR}/templates"

# Function to print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check if required Python packages are installed
    python3 -c "import markdown, jinja2, weasyprint" 2>/dev/null || {
        log_warning "Some Python dependencies are missing"
        log_info "Installing requirements..."
        
        if [ -f "${REPO_ROOT}/requirements.txt" ]; then
            python3 -m pip install -r "${REPO_ROOT}/requirements.txt" --user || {
                log_error "Failed to install Python dependencies"
                exit 1
            }
        else
            log_error "requirements.txt not found"
            exit 1
        fi
    }
    
    log_success "All dependencies are available"
}

# Function to validate directories
validate_directories() {
    log_info "Validating directories..."
    
    if [ ! -d "$IDEASHEETS_DIR" ]; then
        log_error "Ideasheets directory not found: $IDEASHEETS_DIR"
        exit 1
    fi
    
    # Create output directory if it doesn't exist
    mkdir -p "$OUTPUT_DIR"
    
    log_success "Directory validation complete"
}

# Function to count markdown files
count_markdown_files() {
    find "$IDEASHEETS_DIR" -name "*.md" -type f | wc -l
}

# Function to process ideasheets
process_ideasheets() {
    log_info "Processing ideasheets from: $IDEASHEETS_DIR"
    
    local file_count=$(count_markdown_files)
    
    if [ "$file_count" -eq 0 ]; then
        log_warning "No markdown files found in $IDEASHEETS_DIR"
        return 0
    fi
    
    log_info "Found $file_count markdown files to process"
    
    # Process files using the Python script
    if python3 "${SCRIPT_DIR}/markdown_processor.py" "$IDEASHEETS_DIR" -o "$OUTPUT_DIR" -v; then
        log_success "Successfully processed ideasheets"
        
        # List generated files
        if [ -d "$OUTPUT_DIR" ]; then
            local html_count=$(find "$OUTPUT_DIR" -name "*.html" -type f | wc -l)
            local pdf_count=$(find "$OUTPUT_DIR" -name "*.pdf" -type f | wc -l)
            
            log_info "Generated files:"
            log_info "  HTML files: $html_count"
            log_info "  PDF files: $pdf_count"
            
            # Show file list if verbose
            if [ "${VERBOSE:-false}" = "true" ]; then
                echo ""
                echo "Output files:"
                find "$OUTPUT_DIR" -type f -name "*.html" -o -name "*.pdf" | sort
            fi
        fi
    else
        log_error "Failed to process ideasheets"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Process markdown ideasheets and convert them to HTML and PDF.

OPTIONS:
    -h, --help      Show this help message
    -v, --verbose   Enable verbose output
    -c, --check     Only check dependencies and validate setup
    --clean         Clean output directory before processing

ENVIRONMENT VARIABLES:
    IDEASHEETS_DIR  Override default ideasheets directory
    OUTPUT_DIR      Override default output directory

EOF
}

# Parse command line arguments
VERBOSE=false
CHECK_ONLY=false
CLEAN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--check)
            CHECK_ONLY=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log_info "Starting ideasheets processing..."
    log_info "Repository root: $REPO_ROOT"
    log_info "Ideasheets directory: $IDEASHEETS_DIR"
    log_info "Output directory: $OUTPUT_DIR"
    
    # Check dependencies
    check_dependencies
    
    # Validate directories
    validate_directories
    
    if [ "$CHECK_ONLY" = "true" ]; then
        log_success "Dependency check completed successfully"
        exit 0
    fi
    
    # Clean output directory if requested
    if [ "$CLEAN" = "true" ]; then
        log_info "Cleaning output directory..."
        rm -rf "$OUTPUT_DIR"/*
        log_success "Output directory cleaned"
    fi
    
    # Process ideasheets
    process_ideasheets
    
    log_success "Ideasheets processing completed successfully!"
}

# Execute main function
main "$@"