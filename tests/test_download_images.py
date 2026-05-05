from download_images import ext_from_content_type, find_image_refs, resolve_url, safe_stem


class TestFindImageRefs:
    def test_finds_external_image(self):
        content = "![Alt text](https://example.com/image.png)"
        refs = find_image_refs(content)
        assert len(refs) == 1
        full, alt, url = refs[0]
        assert alt == "Alt text"
        assert url == "https://example.com/image.png"

    def test_finds_multiple_images(self):
        content = "![A](https://a.com/a.png)\n![B](https://b.com/b.jpg)"
        assert len(find_image_refs(content)) == 2

    def test_ignores_local_images(self):
        content = "![Local](assets/image.png)"
        assert find_image_refs(content) == []

    def test_ignores_wikilink_images(self):
        content = "![[local-image.png]]"
        assert find_image_refs(content) == []

    def test_empty_content(self):
        assert find_image_refs("") == []


class TestResolveUrl:
    def test_plain_url_unchanged(self):
        url = "https://example.com/image.png"
        assert resolve_url(url) == url

    def test_substack_cdn_decoded(self):
        original = "https://example.com/img.png"
        import urllib.parse
        encoded = urllib.parse.quote(original, safe="")
        cdn = f"https://substackcdn.com/image/fetch/f_auto/{encoded}"
        assert resolve_url(cdn) == original


class TestExtFromContentType:
    def test_jpeg(self):
        assert ext_from_content_type("image/jpeg", "") == ".jpg"

    def test_png(self):
        assert ext_from_content_type("image/png", "") == ".png"

    def test_with_charset(self):
        assert ext_from_content_type("image/png; charset=utf-8", "") == ".png"

    def test_fallback_from_url(self):
        assert ext_from_content_type("application/octet-stream", "https://x.com/img.jpg") == ".jpg"

    def test_fallback_jpeg_to_jpg(self):
        assert ext_from_content_type("application/octet-stream", "https://x.com/img.jpeg") == ".jpg"

    def test_unknown_defaults_to_png(self):
        assert ext_from_content_type("application/octet-stream", "https://x.com/img") == ".png"


class TestSafeStem:
    def test_sanitizes_spaces(self):
        assert safe_stem("my article title") == "my_article_title"

    def test_sanitizes_special_chars(self):
        assert safe_stem("hello/world!") == "hello_world"

    def test_truncates_long_names(self):
        long_name = "a" * 100
        assert len(safe_stem(long_name)) <= 50

    def test_empty_name_returns_source(self):
        assert safe_stem("") == "source"

    def test_collapses_multiple_underscores(self):
        assert "__" not in safe_stem("hello   world")
