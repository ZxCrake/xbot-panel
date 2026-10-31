"""HTML -> content_state and the ArticleEntity* publishing sequence."""
from xbot.x import actions, articles, constants


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, payload, referer):
        self.calls.append({"url": url, "payload": payload, "referer": referer})
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


def _draft_response(rest_id="111"):
    return FakeResponse({"data": {"articleentity_draft_create": {
        "article_entity_results": {"result": {"rest_id": rest_id}}}}})


def _ok_response():
    return FakeResponse({"data": {"ok": True}})


def _publish_response(tweet_id="999"):
    return FakeResponse({"data": {"articleentity_publish": {
        "article_entity_results": {"result": {"metadata": {
            "tweet_results": {"result": {"rest_id": tweet_id}}}}}}}})


def test_content_state_blocks_and_inline_styles():
    cs = articles.content_state_from_html(
        '<div>Hello</div><div><b>Bold</b> and <a href="https://x.com">link</a></div>')
    assert len(cs["blocks"]) == 2
    assert cs["blocks"][0]["text"] == "Hello"
    assert cs["blocks"][0]["type"] == "unstyled"
    second = cs["blocks"][1]
    assert second["text"] == "Bold and link"
    assert second["inline_style_ranges"] == [
        {"offset": 0, "length": 4, "style": "Bold"}]
    assert len(second["entity_ranges"]) == 1
    rng = second["entity_ranges"][0]
    assert rng["offset"] == 9 and rng["length"] == 4
    assert cs["entity_map"][0]["value"]["data"]["url"] == "https://x.com"
    assert len({b["key"] for b in cs["blocks"]}) == 2


def test_subtitle_becomes_header_two():
    cs = articles.content_state_from_html("<div>Body</div>", subtitle="Sub")
    assert cs["blocks"][0]["type"] == "header-two"
    assert cs["blocks"][0]["text"] == "Sub"
    assert cs["blocks"][1]["text"] == "Body"


def test_headings_lists_quotes():
    cs = articles.content_state_from_html(
        "<h1>Title</h1><h2>Sub</h2><ul><li>One</li></ul>"
        "<ol><li>First</li></ol><blockquote>Quote</blockquote>")
    assert [b["type"] for b in cs["blocks"]] == [
        "header-one", "header-two", "unordered-list-item",
        "ordered-list-item", "blockquote"]


def test_mentions_hashtags_cashtags_spans():
    cs = articles.content_state_from_html(
        "<div>Salut @Judor et @x #crypto $BTC</div>")
    data = cs["blocks"][0]["data"]
    assert data["mentions"] == [
        {"from_index": 6, "to_index": 12, "text": "@Judor"},
        {"from_index": 16, "to_index": 18, "text": "@x"},
    ]
    assert data["hashtags"] == [
        {"from_index": 19, "to_index": 26, "text": "#crypto"}]
    assert data["cashtags"] == [
        {"from_index": 27, "to_index": 31, "text": "$BTC"}]


def test_mention_inside_link_is_not_duplicated():
    cs = articles.content_state_from_html(
        '<div><a href="https://x.com/@Judor">@Judor</a></div>')
    block = cs["blocks"][0]
    assert "mentions" not in block["data"]
    assert len(block["entity_ranges"]) == 1


def test_email_is_not_a_mention():
    cs = articles.content_state_from_html("<div>foo@bar.com</div>")
    assert "mentions" not in cs["blocks"][0]["data"]


def test_plain_text_body_mentions():
    cs = articles.content_state_from_html("Salut @Judor")
    assert cs["blocks"][0]["data"]["mentions"] == [
        {"from_index": 6, "to_index": 12, "text": "@Judor"}]


def test_empty_body_gets_one_block():
    cs = articles.content_state_from_html("")
    assert len(cs["blocks"]) == 1
    assert cs["blocks"][0]["text"] == ""
    assert cs["blocks"][0]["type"] == "unstyled"


def test_publish_article_sequence_without_cover():
    session = FakeSession([_draft_response("111"), _ok_response(),
                           _ok_response(), _publish_response("999")])
    ok, ref = actions.publish_article(session, {
        "title": "Hello", "subtitle": "Sub", "body": "<div>Body</div>"})
    assert ok is True and ref == "999"
    assert [c["url"].rsplit("/", 1)[-1] for c in session.calls] == [
        "ArticleEntityDraftCreate", "ArticleEntityUpdateTitle",
        "ArticleEntityUpdateContent", "ArticleEntityPublish"]
    draft, title, content, publish = session.calls
    assert draft["payload"]["variables"] == {
        "content_state": {"blocks": [], "entity_map": []}, "title": "Hello"}
    assert "https://x.com/compose/articles" in draft["referer"]
    assert title["payload"]["variables"] == {
        "articleEntityId": "111", "title": "Hello"}
    assert "compose/articles/edit/111" in title["referer"]
    assert content["payload"]["variables"]["article_entity"] == "111"
    assert content["payload"]["variables"]["content_state"]["blocks"]
    assert publish["payload"]["variables"] == {
        "articleEntityId": "111", "visibilitySetting": "Public"}
    for call in session.calls:
        assert call["payload"]["features"] == constants.ARTICLE_FEATURES
        assert call["payload"]["queryId"]


def test_publish_article_with_cover():
    session = FakeSession([_draft_response("222"), _ok_response(),
                           _ok_response(), _ok_response(),
                           _publish_response("1000")])
    ok, ref = actions.publish_article(session, {
        "title": "T", "body": "<p>b</p>", "cover_media_id": "media-1"})
    assert ok is True and ref == "1000"
    assert [c["url"].rsplit("/", 1)[-1] for c in session.calls] == [
        "ArticleEntityDraftCreate", "ArticleEntityUpdateTitle",
        "ArticleEntityUpdateContent", "ArticleEntityUpdateCoverMedia",
        "ArticleEntityPublish"]
    assert session.calls[3]["payload"]["variables"] == {
        "articleEntityId": "222",
        "coverMedia": {"media_id": "media-1",
                       "media_category": "DraftTweetImage"}}


def test_publish_article_requires_title():
    session = FakeSession([])
    ok, err = actions.publish_article(session, {"title": "", "body": ""})
    assert ok is False and "title" in err
    assert session.calls == []


def test_publish_article_stops_on_failure():
    session = FakeSession([_draft_response("333"),
                           FakeResponse({"errors": [{"message": "nope"}]})])
    ok, err = actions.publish_article(session, {"title": "T", "body": "<p>x</p>"})
    assert ok is False
    assert "ArticleEntityUpdateTitle" in err
    assert len(session.calls) == 2
