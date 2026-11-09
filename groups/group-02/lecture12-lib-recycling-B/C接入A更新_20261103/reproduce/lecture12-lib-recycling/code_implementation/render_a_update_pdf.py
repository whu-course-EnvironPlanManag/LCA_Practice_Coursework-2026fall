"""Render the current A-update report independently of the historical final PDF."""
import build_final_pdf
from integrate_a_supplement import DELIVERY,REPORT

if __name__=='__main__':
    build_final_pdf.DELIVERY=DELIVERY
    build_final_pdf.REPORT=REPORT
    build_final_pdf.main()
