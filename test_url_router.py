"""
AI Video Assistant — URL Router Verification Script
===================================================
Tests URL classification, cloud-share transformation, and SSRF rejection
across the required test URLs:
  1. YouTube URL
  2. Direct .mp4 link
  3. Vimeo link
  4. Google Drive share link
  5. Dropbox link
  6. http://localhost:8000 (SSRF rejection check)
"""

import sys
from utils.url_router import (
    classify_url,
    validate_safe_url,
    is_ip_blocked,
    SSRFBlockedError
)

def run_tests():
    print("=" * 70)
    print("  AI Video Assistant — URL Router & SSRF Defense Verification")
    print("=" * 70)

    test_cases = [
        {
            "name": "1. YouTube Link",
            "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
            "expected_type": "youtube",
            "check": lambda res: res["type"] == "youtube"
        },
        {
            "name": "2. Direct .mp4 Link",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "expected_type": "direct_media",
            "check": lambda res: res["type"] == "direct_media"
        },
        {
            "name": "3. Vimeo Link",
            "url": "https://vimeo.com/76979871",
            "expected_type": "generic_video",
            "check": lambda res: res["type"] == "generic_video"
        },
        {
            "name": "4. Google Drive Share Link",
            "url": "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/view",
            "expected_type": "cloud_share",
            "check": lambda res: res["type"] == "cloud_share" and "export=download" in res["target_url"] and "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs" in res["target_url"]
        },
        {
            "name": "5. Dropbox Link",
            "url": "https://www.dropbox.com/s/sample/video.mp4?dl=0",
            "expected_type": "cloud_share",
            "check": lambda res: res["type"] == "cloud_share" and "dl=1" in res["target_url"]
        },
    ]

    all_passed = True

    # Run classification tests
    for tc in test_cases:
        print(f"\n[TEST] {tc['name']}")
        print(f"       Input URL: {tc['url']}")
        try:
            res = classify_url(tc["url"])
            passed = tc["check"](res)
            status_icon = "[PASS]" if passed else "[FAIL]"
            print(f"       Result: type='{res['type']}', label='{res.get('label')}'")
            print(f"       Target: {res.get('target_url')}")
            print(f"       Status: {status_icon}")
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"       Status: [FAIL] UNEXPECTED EXCEPTION: {e}")
            all_passed = False

    # Run SSRF rejection test on http://localhost:8000
    print("\n[TEST] 6. http://localhost:8000 (SSRF Protection)")
    print("       Input URL: http://localhost:8000")
    try:
        res = classify_url("http://localhost:8000")
        print(f"       Status: [FAIL] -- localhost was NOT blocked! Result: {res}")
        all_passed = False
    except SSRFBlockedError as e:
        print(f"       Status: [PASS] -- correctly blocked with SSRFBlockedError:")
        print(f"               \"{e}\"")
    except Exception as e:
        print(f"       Status: [FAIL] -- wrong exception type: {type(e).__name__}: {e}")
        all_passed = False

    # Additional SSRF protection checks (127.0.0.1, 10.0.0.1, 169.254.169.254, [::1])
    extra_ssrf = [
        "http://127.0.0.1:8000",
        "http://10.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]:8000"
    ]
    print("\n[TEST] 7. Additional Restricted IP Ranges (127.0.0.1, 10.0.0.1, AWS metadata, IPv6 ::1)")
    for u in extra_ssrf:
        try:
            classify_url(u)
            print(f"       [FAIL] -- {u} was NOT blocked!")
            all_passed = False
        except SSRFBlockedError:
            print(f"       [PASS] -- correctly blocked: {u}")

    print("\n" + "=" * 70)
    if all_passed:
        print("  ALL URL ROUTER AND SECURITY TESTS COMPLETED SUCCESSFULLY!")
    else:
        print("  SOME TESTS FAILED! CHECK OUTPUT ABOVE.")
    print("=" * 70)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(run_tests())
