"""
OpenCV preprocessing for scanned Government Orders.
"""

from io import BytesIO


import cv2
import fitz
import numpy as np


class ImagePreprocessingError(Exception):
    """Raised when image preprocessing fails."""


class ImagePreprocessor:
    """
    Preprocesses scanned Government Order pages.

    Processing steps:
        1. Render PDF page.
        2. Convert to grayscale.
        3. Reduce noise.
        4. Apply Otsu binarization.
        5. Correct page skew.
    """

    DPI = 200

    def process_pdf(
        self,
        pdf_content: bytes,
    ) -> list[bytes]:
        """
        Preprocess all pages of a scanned PDF.

        Args:
            pdf_content: Original PDF bytes.

        Returns:
            List of processed PNG images.
        """
        try:
            document = fitz.open(
                stream=BytesIO(pdf_content),
                filetype="pdf",
            )

        except (
            fitz.FileDataError,
            RuntimeError,
        ) as exc:
            raise ImagePreprocessingError(
                "Unable to open scanned PDF."
            ) from exc

        processed_pages: list[bytes] = []

        try:
            for page in document:
                image = self._render_page(
                    page
                )

                processed = (
                    self._preprocess_image(
                        image
                    )
                )

                encoded = self._encode_png(
                    processed
                )

                processed_pages.append(
                    encoded
                )

        finally:
            document.close()

        return processed_pages

    def _render_page(
        self,
        page: fitz.Page,
    ) -> np.ndarray:
        """
        Render a PDF page to an OpenCV image.

        Args:
            page: PyMuPDF page.

        Returns:
            BGR image.
        """
        scale = self.DPI / 72

        matrix = fitz.Matrix(
            scale,
            scale,
        )

        pixmap = page.get_pixmap(
            matrix=matrix,
            colorspace=fitz.csRGB,
            alpha=False,
        )

        image = np.frombuffer(
            pixmap.samples,
            dtype=np.uint8,
        )

        image = image.reshape(
            pixmap.height,
            pixmap.width,
            pixmap.n,
        )

        return cv2.cvtColor(
            image,
            cv2.COLOR_RGB2BGR,
        )

    def _preprocess_image(
        self,
        image: np.ndarray,
    ) -> np.ndarray:
        """
        Apply OpenCV preprocessing.

        Args:
            image: Original rendered image.

        Returns:
            Preprocessed binary image.
        """
        grayscale = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        denoised = cv2.GaussianBlur(
            grayscale,
            (5, 5),
            0,
        )

        _, binary = cv2.threshold(
            denoised,
            0,
            255,
            cv2.THRESH_BINARY
            + cv2.THRESH_OTSU,
        )

        deskewed = self._deskew(
            binary
        )

        return deskewed

    @staticmethod
    def _deskew(
        image: np.ndarray,
    ) -> np.ndarray:
        """
        Correct small text/page rotation.

        Args:
            image: Binary image.

        Returns:
            Deskewed image.
        """
        inverted = cv2.bitwise_not(
            image
        )

        coordinates = np.column_stack(
            np.where(inverted > 0)
        )

        if len(coordinates) < 10:
            return image

        angle = cv2.minAreaRect(
            coordinates
        )[-1]

        if angle < -45:
            angle = -(90 + angle)

        else:
            angle = -angle

        if abs(angle) < 0.1:
            return image

        height, width = image.shape[:2]

        center = (
            width // 2,
            height // 2,
        )

        rotation_matrix = cv2.getRotationMatrix2D(
            center,
            angle,
            1.0,
        )

        return cv2.warpAffine(
            image,
            rotation_matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    @staticmethod
    def _encode_png(
        image: np.ndarray,
    ) -> bytes:
        """
        Encode processed image as PNG.

        Args:
            image: Processed image.

        Returns:
            PNG bytes.
        """
        success, encoded = cv2.imencode(
            ".png",
            image,
        )

        if not success:
            raise ImagePreprocessingError(
                "Unable to encode processed page."
            )

        return encoded.tobytes()


image_preprocessor = ImagePreprocessor()