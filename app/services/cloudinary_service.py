import hashlib
import time
import logging
from typing import Optional, List, Dict, Any
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


def extract_public_id(url: Optional[str]) -> Optional[str]:
    """
    Extracts Cloudinary public_id (including directory prefix) from a Cloudinary URL or raw public_id.
    
    Examples:
      - https://res.cloudinary.com/fzmhtzto/image/upload/v1727521345/cfsi_portal/photo_123.jpg
        => cfsi_portal/photo_123
      - https://res.cloudinary.com/fzmhtzto/image/upload/c_fill,w_300/v1727521345/sample.png
        => sample
      - cfsi_portal/photo_123
        => cfsi_portal/photo_123
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()
    if not url:
        return None

    if "res.cloudinary.com" not in url:
        # If it doesn't look like an absolute URL or data URL, it may already be a raw public_id
        if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("data:"):
            return url.rsplit(".", 1)[0]
        return None

    parts = url.split("/image/upload/")
    if len(parts) < 2:
        return None

    # Strip query parameters or URL anchors
    path = parts[1].split("?")[0].split("#")[0]
    segments = path.split("/")

    valid_segments = []
    for i, seg in enumerate(segments):
        # Version segment, e.g. v1727521345
        if seg.startswith("v") and seg[1:].isdigit():
            remainder = "/".join(segments[i + 1:])
            return remainder.rsplit(".", 1)[0]
        # Ignore transformation segment (e.g. c_fill,w_300 or f_auto,q_auto)
        if any(seg.startswith(p) for p in [
            "c_", "w_", "h_", "q_", "f_", "b_", "e_", "l_", "o_", "r_", "s_", "a_", "fl_", "t_"
        ]) or "," in seg:
            continue
        valid_segments.append(seg)

    if valid_segments:
        return "/".join(valid_segments).rsplit(".", 1)[0]

    return None


class CloudinaryService:
    """Async Cloudinary service for media uploads and auto-cleanup deletions."""

    @property
    def is_configured(self) -> bool:
        """Returns True if full API credentials (including secret) are present for deletion."""
        return bool(
            settings.CLOUDINARY_CLOUD_NAME and
            settings.CLOUDINARY_API_KEY and
            settings.CLOUDINARY_API_SECRET
        )

    def generate_signature(self, params_to_sign: Dict[str, Any]) -> str:
        """
        Computes Cloudinary SHA-1 signature.
        Parameters are sorted alphabetically by key and formatted as key1=val1&key2=val2<secret>.
        """
        sorted_keys = sorted(params_to_sign.keys())
        query_string = "&".join(f"{k}={params_to_sign[k]}" for k in sorted_keys if params_to_sign[k] is not None)
        to_sign = f"{query_string}{settings.CLOUDINARY_API_SECRET}"
        return hashlib.sha1(to_sign.encode("utf-8")).hexdigest()

    async def delete_image(self, url_or_public_id: Optional[str]) -> bool:
        """
        Permanently destroys an image asset from Cloudinary storage and CDN.
        Safe against network errors: logs and returns False on failure without crashing callers.
        """
        if not url_or_public_id:
            return False

        public_id = extract_public_id(url_or_public_id)
        if not public_id:
            return False

        if not self.is_configured:
            logger.warning(
                f"[Cloudinary] Cannot delete asset '{public_id}': CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET "
                f"not configured in backend environment."
            )
            return False

        cloud_name = settings.CLOUDINARY_CLOUD_NAME
        timestamp = int(time.time())

        params = {
            "invalidate": "true",
            "public_id": public_id,
            "timestamp": timestamp,
        }
        signature = self.generate_signature(params)

        post_data = {
            **params,
            "api_key": settings.CLOUDINARY_API_KEY,
            "signature": signature,
        }

        endpoint = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/destroy"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(endpoint, data=post_data)
                data = res.json()
                result = data.get("result")
                if res.status_code == 200 and result in ("ok", "not found"):
                    logger.info(f"[Cloudinary] Destroyed asset '{public_id}' (result: {result})")
                    return True
                else:
                    logger.warning(
                        f"[Cloudinary] Destroy failed for '{public_id}' (status {res.status_code}): {data}"
                    )
                    return False
        except Exception as e:
            logger.error(f"[Cloudinary] Error destroying asset '{public_id}': {e}")
            return False

    async def delete_images(self, urls_or_ids: List[str]) -> int:
        """
        Batch deletes multiple Cloudinary image assets concurrently.
        Returns the number of successfully destroyed assets.
        """
        import asyncio
        if not urls_or_ids:
            return 0

        # Filter out empty or duplicate public IDs
        unique_ids = set()
        for item in urls_or_ids:
            p_id = extract_public_id(item)
            if p_id:
                unique_ids.add(p_id)

        if not unique_ids:
            return 0

        tasks = [self.delete_image(p_id) for p_id in unique_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return sum(1 for r in results if r is True)

    async def upload_image(
        self,
        file_bytes: bytes,
        filename: str = "upload.jpg",
        folder: str = "cfsi_portal"
    ) -> Dict[str, Any]:
        """
        Uploads image file bytes to Cloudinary.
        Uses signed upload if API credentials are present; otherwise uses unsigned preset 'cfsi_uploads'.
        """
        cloud_name = settings.CLOUDINARY_CLOUD_NAME or "fzmhtzto"
        endpoint = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
        timestamp = int(time.time())

        data: Dict[str, Any] = {"folder": folder}
        if self.is_configured:
            params = {"folder": folder, "timestamp": timestamp}
            data["timestamp"] = timestamp
            data["api_key"] = settings.CLOUDINARY_API_KEY
            data["signature"] = self.generate_signature(params)
        else:
            data["upload_preset"] = "cfsi_uploads"

        files = {"file": (filename, file_bytes)}

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(endpoint, data=data, files=files)
            if res.status_code >= 400:
                raise Exception(f"Cloudinary upload failed ({res.status_code}): {res.text}")
            return res.json()


cloudinary_service = CloudinaryService()
