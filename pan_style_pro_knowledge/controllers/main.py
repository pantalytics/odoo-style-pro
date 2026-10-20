from odoo import http
from odoo.http import request


class PanKnowledgeTree(http.Controller):

    @http.route("/pan_style_pro/knowledge/parents", type="jsonrpc", auth="public", website=True, readonly=True)
    def parents(self, article_ids):
        """The ids among ``article_ids`` that have a child the caller may read.

        The public sidebar only knows a page has children once it is unfolded,
        so every row looks the same. Only children the caller can open count:
        the answer never says more than unfolding the row would.
        """
        Article = request.env["knowledge.article"]
        ids = [int(i) for i in article_ids][:500]
        domain = [("parent_id", "in", ids)]
        if "is_article_item" in Article._fields:
            domain.append(("is_article_item", "=", False))
        children = Article.sudo().search(domain).with_env(request.env)._filtered_access("read")
        return children.sudo().parent_id.ids
