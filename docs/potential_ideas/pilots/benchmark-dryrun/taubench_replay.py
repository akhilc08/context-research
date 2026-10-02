"""Replay every τ-bench task's gold actions with a stub user, so no LLM is ever called.

A perfect agent would score 1.0 on every task. Any other score means the install,
environment, or grader is not working as expected.
"""
from tau_bench.envs.retail.env import MockRetailDomainEnv
from tau_bench.envs.airline.env import MockAirlineDomainEnv
from tau_bench.envs.user import BaseUserSimulationEnv
from tau_bench.types import Action, RESPOND_ACTION_NAME


class StubUser(BaseUserSimulationEnv):
    calls = 0

    def reset(self, instruction: str) -> str:
        StubUser.calls += 1
        return "Hi, I need help."

    def step(self, content: str) -> str:
        StubUser.calls += 1
        return "Okay, thanks."

    def get_total_cost(self) -> float:
        return 0.0


def replay(env_cls, split):
    env = env_cls(user_strategy="human", task_split=split, task_index=0)
    env.user = StubUser()
    scores = []
    for i, task in enumerate(env.tasks):
        env.reset(task_index=i)
        for action in task.actions:
            if action.name != RESPOND_ACTION_NAME and action.name not in env.terminate_tools:
                env.step(action)
        if task.outputs:
            env.step(Action(name=RESPOND_ACTION_NAME, kwargs={"content": " ".join(task.outputs)}))
        scores.append(env.calculate_reward().reward)
    failed = [i for i, s in enumerate(scores) if s != 1.0]
    print(f"{env_cls.__name__:22s} split={split:5s} tasks={len(scores):4d} "
          f"perfect={sum(s == 1.0 for s in scores):4d} failed={len(failed)} {failed[:10]}")
    return env


if __name__ == "__main__":
    replay(MockRetailDomainEnv, "test")
    replay(MockAirlineDomainEnv, "test")
    env = replay(MockRetailDomainEnv, "train")
    print(f"stub user calls={StubUser.calls} (all stub, zero LLM calls)")
    print(f"retail policy (wiki) length: {len(env.wiki)} chars, rules: {len(env.rules)}")
