"""Small HTTP client for Tally Prime's local XML/HTTP interface."""

from __future__ import annotations

import requests


class TallyError(RuntimeError):
    """Raised when Tally rejects a request or cannot be reached."""


class TallyClient:

    def __init__(
        self,
        host: str,
        port: int = 9000,
        timeout: int = 10
    ) -> None:

        self.url = f"http://{host}:{port}"
        self.timeout = timeout

    def post_xml(
        self,
        xml_data: str
    ) -> str:

        try:

            response = requests.post(
                self.url,
                data=xml_data.encode("utf-8"),
                headers={
                    "Content-Type":
                    "text/xml; charset=utf-8"
                },
                timeout=self.timeout
            )

            response.raise_for_status()

        except requests.RequestException as exc:

            raise TallyError(
                f"Unable to connect to Tally at "
                f"{self.url}: {exc}"
            ) from exc

        return response.text

    def test_connection(
        self
    ) -> tuple[bool, str]:

        """
        Send a harmless company/list request
        to verify the Tally endpoint.
        """

        xml = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>List of Companies</ID>
  </HEADER>

  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""

        try:

            response = self.post_xml(xml)

            return True, response

        except TallyError as exc:

            return False, str(exc)