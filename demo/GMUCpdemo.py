# -*- coding: utf-8 -*-c
import pytorch_lightning as pl
from pytorch_lightning import seed_everything
from unKR.utils import *
from unKR.data.Sampler import *


def main(arg_path):
    print('This demo is for testing GMUCp')
    args = setup_parser()  # 设置参数
    args = load_config(args, arg_path)
    seed_everything(args.seed)
    print(args.model_name)

    """set up sampler to datapreprocess"""  # 设置数据处理的采样过程
    train_sampler_class = import_class(f"unKR.data.{args.train_sampler_class}")
    train_sampler = train_sampler_class(args)  # 这个sampler是可选择的
    # print(train_sampler)
    test_sampler_class = import_class(f"unKR.data.{args.test_sampler_class}")
    test_sampler = test_sampler_class(train_sampler)  # test_sampler是一定要的

    """set up datamodule"""  # 设置数据模块
    data_class = import_class(f"unKR.data.{args.data_class}")  # 定义数据类 DataClass
    kgdata = data_class(args, train_sampler, test_sampler)

    """set up model"""
    model_class = import_class(f"unKR.model.{args.model_name}")
    model = model_class(args, args.num_symbols, None)

    """set up lit_model"""
    litmodel_class = import_class(f"unKR.lit_model.{args.litmodel_name}")
    lit_model = litmodel_class(model, train_sampler, args)

    """set up logger"""
    logger = pl.loggers.TensorBoardLogger("training/logs")
    if args.use_wandb:
        log_name = "_".join([args.model_name, args.dataset_name, str(args.lr)])
        logger = pl.loggers.WandbLogger(name=log_name, project="unKR")
        logger.log_hyperparams(vars(args))

    """early stopping"""
    early_callback = pl.callbacks.EarlyStopping(
        monitor="Eval_hits@10",
        mode="max",
        patience=args.early_stop_patience,
        check_on_train_epoch_end=False,
    )

    """set up model save method"""
    # 目前是保存在验证集上MSE结果最好的模型
    # 模型保存的路径
    dirpath = "/".join(["output", args.eval_task, args.dataset_name, args.model_name])
    model_checkpoint = pl.callbacks.ModelCheckpoint(
        monitor="Eval_hits@10",
        mode="max",
        filename="{epoch}-{Eval_hits@10:.5f}",
        dirpath=dirpath,
        save_weights_only=True,
        save_top_k=1,
    )
    callbacks = [early_callback, model_checkpoint]
    # initialize trainer
    trainer = pl.Trainer.from_argparse_args(
        args,
        callbacks=callbacks,
        logger=logger,
        default_root_dir="training/logs",
        gpus="0,",
        check_val_every_n_epoch=args.check_val_every_n_epoch,
    )
    '''保存参数到config'''
    if args.save_config:
        save_config(args)

    if not args.test_only:
        # train&valid
        trainer.fit(lit_model, datamodule=kgdata)
        # 加载本次实验中dev上表现最好的模型，进行test
        path = model_checkpoint.best_model_path
    else:
        # path = args.checkpoint_dir
        path = "./output/confidence_prediction/nl27k/GMUCp/epoch=749-Eval_hits@10=0.63200.ckpt"
    lit_model.load_state_dict(torch.load(path)["state_dict"])
    lit_model.eval()
    trainer.test(lit_model, datamodule=kgdata)


if __name__ == "__main__":
    main(arg_path='config/nl27k/GMUCp_nl27k.yaml')
