#!/bin/bash
#
# Process Ideasheets Script
# This script processes markdown files in the ideasheets directory
# and converts them to HTML and PDF with enhanced features.
# Enhanced with reliability and error recovery mechanisms.
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

# Reliability settings
MAX_RETRIES=3
RETRY_DELAY=2
TIMEOUT_SECONDS=300
HEALTH_CHECK_INTERVAL=30

# Lock file for preventing concurrent executions
LOCK_FILE="/tmp/process_ideasheets.lock"

# Cleanup function
cleanup() {
    local exit_code=$?
    log_info "Cleaning up..."
    
    # Remove lock file
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
    fi
    
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
    
    if [ $exit_code -eq 0 ]; then
        log_success "Script completed successfully"
    else
        log_error "Script exited with error code: $exit_code"
    fi
    
    exit $exit_code
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Function to acquire lock
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        
        # Check if process is still running
        if [ -n "$lock_pid" ] && kill -0 "$lock_pid" 2>/dev/null; then
            log_error "Another instance is already running (PID: $lock_pid)"
            exit 1
        else
            log_warning "Removing stale lock file"
            rm -f "$LOCK_FILE"
        fi
    fi
    
    echo $$ > "$LOCK_FILE"
    log_info "Lock acquired (PID: $$)"
}

# Function to print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Function to retry commands
retry_command() {
    local command="$1"
    local description="$2"
    local attempt=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        log_info "Attempting $description (attempt $attempt/$MAX_RETRIES)"
        
        if eval "$command"; then
            log_success "$description completed successfully"
            return 0
        else
            local exit_code=$?
            if [ $attempt -eq $MAX_RETRIES ]; then
                log_error "$description failed after $MAX_RETRIES attempts"
                return $exit_code
            else
                log_warning "$description failed (attempt $attempt), retrying in ${RETRY_DELAY}s..."
                sleep $RETRY_DELAY
                ((attempt++))
            fi
        fi
    done
}

# Function to run command with timeout
run_with_timeout() {
    local timeout="$1"
    local command="$2"
    local description="$3"
    
    log_info "Running $description with ${timeout}s timeout"
    
    if timeout "$timeout" bash -c "$command"; then
        log_success "$description completed within timeout"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            log_error "$description timed out after ${timeout}s"
        else
            log_error "$description failed with exit code: $exit_code"
        fi
        return $exit_code
    fi
}

# Function to check system health
check_system_health() {
    log_info "Checking system health..."
    
    # Check available disk space
    local available_space
    available_space=$(df "$REPO_ROOT" | awk 'NR==2 {print $4}')
    local min_space=1048576  # 1GB in KB
    
    if [ "$available_space" -lt "$min_space" ]; then
        log_error "Insufficient disk space: ${available_space}KB available, ${min_space}KB required"
        return 1
    fi
    
    # Check memory usage
    local memory_usage
    memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2 }')
    
    if [ "$memory_usage" -gt 90 ]; then
        log_warning "High memory usage: ${memory_usage}%"
    fi
    
    # Check if required commands are available
    local required_commands=("python3" "find" "wc")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            return 1
        fi
    done
    
    log_success "System health check passed"
    return 0
}

# Function to monitor process health
monitor_process_health() {
    local process_pid="$1"
    local description="$2"
    
    while kill -0 "$process_pid" 2>/dev/null; do
        sleep $HEALTH_CHECK_INTERVAL
        
        # Check if process is consuming too much memory
        local memory_mb
        memory_mb=$(ps -o rss= -p "$process_pid" 2>/dev/null | awk '{print int($1/1024)}' || echo "0")
        
        if [ "$memory_mb" -gt 1000 ]; then  # 1GB
            log_warning "Process $process_pid ($description) using high memory: ${memory_mb}MB"
        fi
    done
}

# Enhanced dependency check with health monitoring
check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check Python with version validation
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check Python version
    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Python version: $python_version"
    
    # Check if required Python packages are installed with health check
    local check_command="python3 -c \"import markdown, jinja2, weasyprint\" 2>/dev/null"
    
    if ! eval "$check_command"; then
        log_warning "Some Python dependencies are missing"
        log_info "Installing requirements..."
        
        if [ -f "${REPO_ROOT}/requirements.txt" ]; then
            # Install with retry mechanism
            if ! retry_command "python3 -m pip install -r \"${REPO_ROOT}/requirements.txt\" --user" "Python dependencies installation"; then
                log_error "Failed to install Python dependencies after retries"
                exit 1
            fi
        else
            log_error "requirements.txt not found"
            exit 1
        fi
    fi
    
    # Verify installation
    if ! retry_command "$check_command" "Python dependencies verification"; then
        log_error "Python dependencies verification failed"
        exit 1
    fi
    
    log_success "All dependencies are available"
}

# Enhanced directory validation with health checks
validate_directories() {
    log_info "Validating directories..."
    
    if [ ! -d "$IDEASHEETS_DIR" ]; then
        log_error "Ideasheets directory not found: $IDEASHEETS_DIR"
        exit 1
    fi
    
    # Check directory permissions
    if [ ! -r "$IDEASHEETS_DIR" ]; then
        log_error "Cannot read ideasheets directory: $IDEASHEETS_DIR"
        exit 1
    fi
    
    # Create output directory if it doesn't exist with retry
    if ! retry_command "mkdir -p \"$OUTPUT_DIR\"" "Output directory creation"; then
        log_error "Failed to create output directory: $OUTPUT_DIR"
        exit 1
    fi
    
    # Check output directory permissions
    if [ ! -w "$OUTPUT_DIR" ]; then
        log_error "Cannot write to output directory: $OUTPUT_DIR"
        exit 1
    fi
    
    log_success "Directory validation complete"
}

# Function to count markdown files
count_markdown_files() {
    find "$IDEASHEETS_DIR" -name "*.md" -type f | wc -l
}

# Enhanced ideasheets processing with monitoring
process_ideasheets() {
    log_info "Processing ideasheets from: $IDEASHEETS_DIR"
    
    local file_count=$(count_markdown_files)
    
    if [ "$file_count" -eq 0 ]; then
        log_warning "No markdown files found in $IDEASHEETS_DIR"
        return 0
    fi
    
    log_info "Found $file_count markdown files to process"
    
    # Process files using the Python script with timeout and monitoring
    local python_command="python3 \"${SCRIPT_DIR}/markdown_processor.py\" \"$IDEASHEETS_DIR\" -o \"$OUTPUT_DIR\" -v"
    
    # Run with timeout and health monitoring
    if run_with_timeout "$TIMEOUT_SECONDS" "$python_command" "markdown processing"; then
        log_success "Successfully processed ideasheets"
        
        # Verify output files were created
        local generated_files=0
        if [ -d "$OUTPUT_DIR" ]; then
            generated_files=$(find "$OUTPUT_DIR" -name "*.html" -o -name "*.pdf" | wc -l)
            log_info "Generated $generated_files output files"
            
            if [ "$generated_files" -gt 0 ]; then
                log_info "Generated files:"
                find "$OUTPUT_DIR" -name "*.html" -o -name "*.pdf" | head -10 | while read -r file; do
                    local size
                    size=$(stat -c%s "$file" 2>/dev/null | numfmt --to=iec-i --suffix=B 2>/dev/null || echo "unknown")
                    log_info "  - $(basename "$file") ($size)"
                done
                
                if [ "$generated_files" -gt 10 ]; then
                    log_info "  ... and $((generated_files - 10)) more files"
                fi
            else
                log_warning "No output files were generated"
                return 1
            fi
        else
            log_warning "Output directory not found after processing"
            return 1
        fi
    else
        log_error "Failed to process ideasheets"
        return 1
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

# Enhanced main execution with reliability features
main() {
    # Acquire lock to prevent concurrent executions
    acquire_lock
    
    log_info "Starting ideasheets processing..."
    log_info "Repository root: $REPO_ROOT"
    log_info "Ideasheets directory: $IDEASHEETS_DIR"
    log_info "Output directory: $OUTPUT_DIR"
    log_info "Script PID: $$"
    
    # System health check
    if ! check_system_health; then
        log_error "System health check failed"
        exit 1
    fi
    
    # Check dependencies with retry
    if ! retry_command "check_dependencies" "dependency check"; then
        log_error "Dependency check failed after retries"
        exit 1
    fi
    
    # Validate directories
    validate_directories
    
    if [ "$CHECK_ONLY" = "true" ]; then
        log_success "Dependency and health checks completed successfully"
        exit 0
    fi
    
    # Clean output directory if requested
    if [ "$CLEAN" = "true" ]; then
        log_info "Cleaning output directory..."
        if ! retry_command "rm -rf \"$OUTPUT_DIR\"/*" "output directory cleanup"; then
            log_warning "Failed to clean output directory completely"
        else
            log_success "Output directory cleaned"
        fi
    fi
    
    # Process ideasheets with health monitoring
    local start_time
    start_time=$(date +%s)
    
    if process_ideasheets; then
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_success "Ideasheets processing completed successfully in ${duration}s!"
        
        # Final health check
        check_system_health || log_warning "System health degraded after processing"
    else
        log_error "Ideasheets processing failed"
        exit 1
    fi
}

# Execute main function with arguments
main "$@"