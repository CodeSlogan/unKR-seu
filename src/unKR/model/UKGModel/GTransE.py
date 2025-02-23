import torch.nn as nn
import torch
import numpy as np
from .model import Model


class GTransE(Model):
    """
    Attributes:
        args: Model configuration parameters.
        epsilon: Calculate embedding_range.
        margin: Calculate embedding_range and loss.
        embedding_range: Uniform distribution range.
        ent_emb: Entity embedding, shape:[num_ent, emb_dim].
        rel_emb: Relation embedding, shape:[num_rel, emb_dim].
    """

    def __init__(self, args):
        super(GTransE, self).__init__(args)
        self.args = args
        self.ent_emb = None
        self.rel_emb = None
        self.norm = 1
        self.alpha = args.alpha
        self.epsilon = 2.0
        self.margin = nn.Parameter(
            torch.Tensor([self.args.margin]),
            requires_grad=False
        )
        self.embedding_range = nn.Parameter(
            torch.Tensor([(self.margin.item() + self.epsilon) / self.args.emb_dim]),
            requires_grad=False
        )

        self.init_emb()

    def init_emb(self):
        """Initialize the entity and relation embeddings in the form of a uniform distribution.

        """
        self.ent_emb = nn.Embedding(self.args.num_ent, self.args.emb_dim)
        self.rel_emb = nn.Embedding(self.args.num_rel, self.args.emb_dim)
        nn.init.uniform_(tensor=self.ent_emb.weight.data, a=-self.embedding_range.item(), b=self.embedding_range.item())
        nn.init.uniform_(tensor=self.rel_emb.weight.data, a=-self.embedding_range.item(), b=self.embedding_range.item())

    def score_func(self, head_emb, relation_emb, tail_emb, mode):
        """Calculating the score of triples.

        Args:
            head_emb: The head entity embedding.
            relation_emb: The relation embedding.
            tail_emb: The tail entity embedding.
            mode: Choose head-predict or tail-predict.

        Returns:
            score: The score of triples.
        """

        score = (head_emb + relation_emb) - tail_emb
        score = - torch.norm(score, p=self.norm, dim=-1)
        score = score.to(self.args.gpu)

        return score

    def forward(self, triples, negs=None, mode='single'):
        """The functions used in the training phase

        Args:
            triples: The triples ids, as (h, r, t), shape:[batch_size, 3].
            negs: Negative samples, defaults to None.
            mode: Choose head-predict or tail-predict, Defaults to 'single'.

        Returns:
            score: The score of triples.+
        """
        triples = triples[:, :3].to(torch.int)
        head_emb, relation_emb, tail_emb = self.tri2emb(triples, negs, mode)
        score = self.score_func(head_emb, relation_emb, tail_emb, mode)

        return score

    def get_score(self, batch, mode):
        """The functions used in the testing phase

        Args:
            batch: A batch of data.
            mode: Choose head-predict or tail-predict.

        Returns:
            score: The score of triples.
        """
        triples = batch["positive_sample"]
        triples = triples[:, :3].to(torch.int)
        triples = triples.to(self.args.gpu)

        # print(triples.device)
        head_emb, relation_emb, tail_emb = self.tri2emb(triples, mode=mode)
        score = self.score_func(head_emb, relation_emb, tail_emb, mode)

        return score
