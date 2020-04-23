from aws_cdk import (
    core, 
    aws_codebuild as codebuild,
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_iam as iam,
)

pipeline_name = 'repo-gpr-lztemplate-pipeline'
codecommit_repo_name = 'repo-gpr-lztemplate-environment'

class PipelineStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        update_pipe = self.CdkDeploySimplePipeline( "Pipeline Update" , 
                                                   codecommit.Repository.from_repository_name(self, "ImportedRepoUpdatePipe", pipeline_name),
                                                   "master",
                                                   codepipeline.Artifact("pipeline"), 
                                                   codepipeline.Artifact("pipeline-output")
                                                  )

        # Pipeline for each branches
        for branch in ["master","dev"] :
            environment_pipe_master =  self.CdkDeploySimplePipeline( "Pipeline Deploy Environment ({})".format(branch) ,
                                                                     repo = codecommit.Repository.from_repository_name(self, "ImportedRepoEnvironment-{}".format(branch), codecommit_repo_name),
                                                                     branch = branch,
                                                                     src = codepipeline.Artifact("environment-{}".format(branch)), 
                                                                     output = codepipeline.Artifact("environment-output-{}".format(branch)))

    def CdkDeployProject(self, name:str, stage:str) :
        return codebuild.PipelineProject(self, name,
            build_spec=codebuild.BuildSpec.from_object(dict(
            version="0.2",
            phases=dict(
                install=dict(
                    commands="npm install -g aws-cdk ; pip install -r requirements.txt"),
                build=dict(commands=[
                    "cdk bootstrap",
                    "cdk deploy --require-approval never -c stage={}".format(stage)])),
                environment=dict(buildImage=codebuild.LinuxBuildImage.STANDARD_2_0)
            )))

    def CdkDeploySimplePipeline( self , name:str , repo, branch:str, src:str, output) :
        cdk_deploy = self.CdkDeployProject("CDK Deploy {}".format(name),stage=branch)
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
                            output=src)]),
                codepipeline.StageProps(stage_name="Deploy",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="CdkDeploy",
                            project=cdk_deploy,
                            input=src,
                            outputs=[output])])
                ]
            )




