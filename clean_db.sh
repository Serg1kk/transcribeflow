#!/bin/bash
# TranscribeFlow Database Cleanup Script
# Usage: ./clean_db.sh [failed|all]

cd "$(dirname "$0")/backend"
source .venv/bin/activate

case "$1" in
    failed)
        echo "Deleting failed transcriptions..."
        python3 -c "
from models import get_db, Transcription, TranscriptionStatus
db = next(get_db())
count = db.query(Transcription).filter(Transcription.status == TranscriptionStatus.FAILED).count()
db.query(Transcription).filter(Transcription.status == TranscriptionStatus.FAILED).delete()
db.commit()
print(f'Deleted {count} failed transcriptions')
"
        ;;
    all)
        echo "Deleting ALL transcriptions..."
        python3 -c "
from models import get_db, Transcription
db = next(get_db())
count = db.query(Transcription).count()
db.query(Transcription).delete()
db.commit()
print(f'Deleted {count} transcriptions')
"
        ;;
    *)
        echo "TranscribeFlow Database Cleanup"
        echo ""
        echo "Usage: ./clean_db.sh [option]"
        echo ""
        echo "Options:"
        echo "  failed  - Delete only failed transcriptions"
        echo "  all     - Delete ALL transcriptions"
        echo ""
        echo "Examples:"
        echo "  ./clean_db.sh failed"
        echo "  ./clean_db.sh all"
        ;;
esac
