#!/bin/bash
# MicroCraft Runner
# Usage: ./run.sh [simple|full] [--live|--ref] [--simple-renderer]

cd "$(dirname "$0")"

# Activate venv
source venv/bin/activate

VERSION="simple"
USE_REF=""
RENDERER=""
DEBUG=""
XMAS=""

# Parse arguments
for arg in "$@"; do
    case $arg in
        simple)
            VERSION="simple"
            ;;
        full)
            VERSION="full"
            ;;
        --live)
            USE_REF=""
            ;;
        --ref)
            USE_REF="--use-ref"
            ;;
        --simple-renderer|--simple)
            RENDERER="--simple-renderer"
            ;;
        --sprites|--sprite-renderer)
            RENDERER=""
            ;;
        --debug)
            DEBUG="--debug"
            ;;
        --xmas)
            XMAS="--xmas"
            ;;
        -h|--help)
            echo "MicroCraft Runner"
            echo ""
            echo "Usage: ./run.sh [VERSION] [OPTIONS]"
            echo ""
            echo "Versions:"
            echo "  simple    Simple version for livecoding (default)"
            echo "  full      Full version with all features"
            echo ""
            echo "Options:"
            echo "  --live             Use live/ code (for livecoding, simple only)"
            echo "  --ref              Use ref/ reference implementation (simple only)"
            echo "  --simple-renderer  Use simple shapes (full only, circles/rectangles)"
            echo "  --sprites          Use sprite renderer (full only, default)"
            echo "  --debug            Debug mode: no fog, AI logs (full only)"
            echo "  --xmas             Christmas mode: festive explosions (full only)"
            echo ""
            echo "Examples:"
            echo "  ./run.sh                         # simple + live (error if not implemented)"
            echo "  ./run.sh simple --ref            # simple + reference implementation"
            echo "  ./run.sh full                    # full version with sprites"
            echo "  ./run.sh full --simple-renderer  # full version with shapes"
            echo "  ./run.sh full --debug            # full with debug mode"
            echo "  ./run.sh full --xmas             # full with Christmas explosions"
            exit 0
            ;;
    esac
done

# Run the game
if [ "$VERSION" = "simple" ]; then
    # Simple mode always uses SimpleRenderer
    echo "Running: python -m simple.main $USE_REF"
    python -m simple.main $USE_REF
else
    echo "Running: python -m full.main $DEBUG $XMAS $RENDERER"
    python -m full.main $DEBUG $XMAS $RENDERER
fi
