from aws_cdk import (
    core, 
    aws_codebuild as codebuild,
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_iam as iam,
)

codecommit_pipeline_name = 'repo-gpr-lztemplate-pipeline'
codecommit_repo_name = 'repo-gpr-lztemplate-environment'
install_commands = 'npm install -g aws-cdk ; pip install -r requirements.txt'

def deploy_commands(stage):
    return ["cdk bootstrap", f"cdk deploy --require-approval never -c stage={stage}"]

class PipelineStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        update_pipe = self.CdkDeploySimplePipeline("CodePipeline",
                                                   codecommit.Repository.from_repository_name(self, "ImportedRepoUpdatePipe", codecommit_pipeline_name),
                                                   "master",
                                                   codepipeline.Artifact("pipeline"), 
                                                   codepipeline.Artifact("pipeline-output")
                                                  )

        # Pipeline for each branches
        for branch in ["master", "dev"] :
            environment_pipe_master =  self.CdkDeploySimplePipeline(f"Infra-{branch}",
                                                                    repo = codecommit.Repository.from_repository_name(self, f"ImportedRepoEnvironment-{branch}", codecommit_repo_name),
                                                                    branch = branch,
                                                                    src = codepipeline.Artifact(f"environment-{branch}"),
                                                                    output = codepipeline.Artifact(f"environment-output-{branch}")
                                                                    )

    def CdkDeploySimplePipeline(self, name:str, repo, branch:str, src:str, output):
        cdk_deploy = self.CdkDeployProject(f"{name}-CDKDeploy", stage=branch)
        cdk_deploy.role.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=["CloudFormation:*","ec2:*","s3:*"]))

        return codepipeline.Pipeline(self, name,
                                     stages=[
                                         codepipeline.StageProps(stage_name="Source",
                                                                 actions=[
                                                                         codepipeline_actions.CodeCommitSourceAction(
                                                                         action_name="CodeCommit_Source",
                                                                         repository=repo,
                                                                         branch=branch,
                                                                         output=src
                                                                         )]),
                                         codepipeline.StageProps(stage_name="Deploy",
                                                                 actions=[
                                                                         codepipeline_actions.CodeBuildAction(
                                                                         action_name="CdkDeploy",
                                                                         project=cdk_deploy,
                                                                         input=src,
                                                                         outputs=[output]
                                                                         )]),
                                         ]
                                    )

    def CdkDeployProject(self, name:str, stage:str) :
        return codebuild.PipelineProject(self, name,
                                         build_spec=codebuild.BuildSpec.from_object(dict(
                                         version="0.2",
                                         phases=dict(
                                                     install=dict(commands=install_commands),
                                                     build=dict(commands=deploy_commands(stage)),
                                                    ),
                                         environment=dict(buildImage=codebuild.LinuxBuildImage.STANDARD_2_0),
                                         environment_variable=dict([["environment", stage]]),
                                         )))
