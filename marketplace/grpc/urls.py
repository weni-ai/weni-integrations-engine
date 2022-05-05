from marketplace.accounts.urls import grpc_handlers as accounts_grpc_handlers


def grpc_handlers(server):
    accounts_grpc_handlers(server)
