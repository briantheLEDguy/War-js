// Unsaved, unregistered native fixtures. Root owns compilation and actual imported-mesh persistence tests.
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarMageReferenceRestore.h"
#include "WarMageReviewLibrary.h"
#include "Animation/Skeleton.h"
#include "Engine/SkeletalMesh.h"
#include "ReferenceSkeleton.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "UObject/Package.h"
#include "UObject/UObjectGlobals.h"
#include "Async/Async.h"
#include <limits>

namespace WarMageReferenceRestoreTests
{
constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter;

FString NewRoot()
{
    return TEXT("/Game/Characters/MageFaceDiagnostic/restore_") + FGuid::NewGuid().ToString(EGuidFormats::Digits).ToLower();
}

UPackage* Package(const FString& Root, const TCHAR* Name)
{
    UPackage* Result = CreatePackage(*(Root + TEXT("/") + Name));
    Result->SetFlags(RF_Transient);
    return Result;
}

USkeleton* Skeleton(const FString& Root, const TCHAR* Name)
{
    USkeleton* Result = NewObject<USkeleton>(Package(Root,Name), FName(Name), RF_Transient | RF_Transactional);
    FReferenceSkeletonModifier Ref(Result);
    Ref.Add(FMeshBoneInfo(TEXT("rig"),TEXT("rig"),INDEX_NONE), FTransform(FQuat::Identity, FVector::ZeroVector, FVector(100)));
    Ref.Add(FMeshBoneInfo(TEXT("root"),TEXT("root"),0), FTransform::Identity);
    Ref.Add(FMeshBoneInfo(TEXT("head"),TEXT("head"),1), FTransform(FVector(0,0,1.65)));
    return Result;
}

USkeletalMesh* Mesh(const FString& Root, const TCHAR* Name, USkeleton* Skeleton)
{
    USkeletalMesh* Result = NewObject<USkeletalMesh>(Package(Root,Name), FName(Name), RF_Transient | RF_Transactional);
    Result->SetSkeleton(Skeleton);
    Result->SetRefSkeleton(Skeleton->GetReferenceSkeleton());
    Result->CalculateInvRefMatrices();
    return Result;
}

void ChangePose(USkeletalMesh* Mesh, FTransform Pose, bool Recalculate=true)
{
    FReferenceSkeleton Reference = Mesh->GetRefSkeleton();
    {
        FReferenceSkeletonModifier Modifier(Reference,Mesh->GetSkeleton());
        Modifier.UpdateRefPoseTransform(2,Pose);
    }
    Mesh->SetRefSkeleton(Reference);
    if (Recalculate)
    {
        Mesh->SetRefBasesInvMatrix(TArray<FMatrix44f>());
        Mesh->CalculateInvRefMatrices();
    }
}

struct FFixture
{
    FString Root=NewRoot();
    FString SourceRoot=TEXT("/Game/WarMageRestoreFixture/") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    USkeleton* OriginalSkeleton=Skeleton(SourceRoot,TEXT("OriginalSkeleton"));
    USkeleton* CopiedSkeleton=DuplicateObject<USkeleton>(OriginalSkeleton,Package(Root,TEXT("CopiedSkeleton")),TEXT("CopiedSkeleton"));
    USkeletalMesh* Original=Mesh(SourceRoot,TEXT("Original"),OriginalSkeleton);
    USkeletalMesh* Candidate=Mesh(Root,TEXT("Candidate"),CopiedSkeleton);

    FFixture()
    {
        CopiedSkeleton->SetFlags(RF_Transient);
        Original->GetOutermost()->SetDirtyFlag(false);
        OriginalSkeleton->GetOutermost()->SetDirtyFlag(false);
        CopiedSkeleton->GetOutermost()->SetDirtyFlag(false);
        Candidate->GetOutermost()->SetDirtyFlag(false);
    }
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageRestoreIsolationTest,
    "AegisWar.Foundation.MageReferenceRestore.Isolation",WarMageReferenceRestoreTests::Flags)
bool FWarMageRestoreIsolationTest::RunTest(const FString& Parameters)
{
    using namespace WarMageReferenceRestoreTests;
    FFixture F;
    const FString Before=UWarMageReviewLibrary::DescribeSkeletalReference(F.Original);
    TestFalse(TEXT("Null destination rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(nullptr,F.Original,F.Root));
    TestFalse(TEXT("Null source rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(F.Candidate,nullptr,F.Root));
    TestFalse(TEXT("Original destination rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(F.Original,F.Original,F.Root));
    TestFalse(TEXT("Wrong private root rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(F.Candidate,F.Original,NewRoot()));
    TestFalse(TEXT("Uppercase private suffix rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(F.Candidate,F.Original,F.Root+TEXT("A")));
    F.Candidate->SetSkeleton(F.OriginalSkeleton);
    TestFalse(TEXT("Shared original skeleton rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(F.Candidate,F.Original,F.Root));
    F.Candidate->SetSkeleton(F.CopiedSkeleton);
    F.Candidate->MarkAsGarbage();
    TestFalse(TEXT("Invalid destination rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(F.Candidate,F.Original,F.Root));
    TestEqual(TEXT("Original reference unchanged on rejection"),UWarMageReviewLibrary::DescribeSkeletalReference(F.Original),Before);
    TestFalse(TEXT("Original package remains clean"),F.Original->GetOutermost()->IsDirty());
    TestFalse(TEXT("Original skeleton remains clean"),F.OriginalSkeleton->GetOutermost()->IsDirty());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageRestoreToleranceTest,
    "AegisWar.Foundation.MageReferenceRestore.Preconditions",WarMageReferenceRestoreTests::Flags)
bool FWarMageRestoreToleranceTest::RunTest(const FString& Parameters)
{
    using namespace WarMageReferenceRestoreTests;
    FFixture LargeLocal;
    ChangePose(LargeLocal.Candidate,FTransform(FVector(0,0,1.652)),false);
    TestTrue(TEXT("Fixture actually exceeds the local tolerance"),
        LargeLocal.Candidate->GetRefSkeleton().GetRefBonePose()[2].GetTranslation().Z -
        LargeLocal.Original->GetRefSkeleton().GetRefBonePose()[2].GetTranslation().Z > .001);
    TestFalse(TEXT("Local probe greater than .001 cm rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(LargeLocal.Candidate,LargeLocal.Original,LargeLocal.Root));
    FFixture LargeInverse;
    auto Inverse=LargeInverse.Candidate->GetRefBasesInvMatrix();Inverse[2].M[3][0]+=.0002f;
    LargeInverse.Candidate->SetRefBasesInvMatrix(Inverse);
    TestFalse(TEXT("Stored inverse probe greater than .0001 cm rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(LargeInverse.Candidate,LargeInverse.Original,LargeInverse.Root));
    FFixture Missing;
    Missing.Candidate->SetRefBasesInvMatrix(TArray<FMatrix44f>());
    TestFalse(TEXT("Missing inverse array rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(Missing.Candidate,Missing.Original,Missing.Root));
    FFixture Stale;
    {
        // Copy before the modifier rebuilds its full pose, reproducing the stale-reference boundary.
        FReferenceSkeleton Ref=Stale.Candidate->GetRefSkeleton();
        FReferenceSkeletonModifier Modifier(Ref,Stale.CopiedSkeleton);
        Modifier.UpdateRefPoseTransform(2,FTransform(FVector(0,0,10)));
        Stale.Candidate->SetRefSkeleton(Ref);
    }
    TestFalse(TEXT("Stale raw/full reference pose rejected before mutation"),
        UWarMageReferenceRestore::RestoreDiagnosticMeshReference(Stale.Candidate,Stale.Original,Stale.Root));
    TestFalse(TEXT("Stale reference rejection leaves transient package clean"),Stale.Candidate->GetOutermost()->IsDirty());
    FFixture DifferentSkeleton;
    {FReferenceSkeletonModifier Modifier(DifferentSkeleton.CopiedSkeleton);Modifier.UpdateRefPoseTransform(2,FTransform(FVector(0,0,1.650001)));}
    TestFalse(TEXT("Copied skeleton reference must be identical"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(DifferentSkeleton.Candidate,DifferentSkeleton.Original,DifferentSkeleton.Root));
    FFixture Names;
    USkeleton* Other=NewObject<USkeleton>(GetTransientPackage(),NAME_None,RF_Transient);
    {FReferenceSkeletonModifier Modifier(Other);Modifier.Add(FMeshBoneInfo(TEXT("other"),TEXT("other"),INDEX_NONE),FTransform::Identity);}
    Names.Candidate->SetRefSkeleton(Other->GetReferenceSkeleton());
    TestFalse(TEXT("Different names/count rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(Names.Candidate,Names.Original,Names.Root));
    FFixture Parents;
    USkeleton* ParentReference=NewObject<USkeleton>(GetTransientPackage(),NAME_None,RF_Transient);
    {FReferenceSkeletonModifier Modifier(ParentReference);
     Modifier.Add(FMeshBoneInfo(TEXT("rig"),TEXT("rig"),INDEX_NONE),FTransform(FQuat::Identity,FVector::ZeroVector,FVector(100)));
     Modifier.Add(FMeshBoneInfo(TEXT("root"),TEXT("root"),0),FTransform::Identity);
     Modifier.Add(FMeshBoneInfo(TEXT("head"),TEXT("head"),0),FTransform(FVector(0,0,1.65)));}
    Parents.Candidate->SetRefSkeleton(ParentReference->GetReferenceSkeleton());
    TestFalse(TEXT("Different parent rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(Parents.Candidate,Parents.Original,Parents.Root));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageRestoreExactTest,
    "AegisWar.Foundation.MageReferenceRestore.ExactCopy",WarMageReferenceRestoreTests::Flags)
bool FWarMageRestoreExactTest::RunTest(const FString& Parameters)
{
    using namespace WarMageReferenceRestoreTests;
    for (const bool DirtyOriginal : {false,true})
    {
        FFixture F;
        F.Original->GetOutermost()->SetDirtyFlag(DirtyOriginal);
        F.OriginalSkeleton->GetOutermost()->SetDirtyFlag(DirtyOriginal);
        const FString OriginalBefore=UWarMageReviewLibrary::DescribeSkeletalReference(F.Original);
        const FString SourceSkeletonBefore=UWarMageReviewLibrary::DescribeSkeletonReference(F.OriginalSkeleton);
        const FString CopiedSkeletonBefore=UWarMageReviewLibrary::DescribeSkeletonReference(F.CopiedSkeleton);
        const FString OriginalDdcGuid=F.Original->GetImportedModel()->GetIdString();
        const FGuid OriginalSkeletonGuid=F.OriginalSkeleton->GetGuid();
        const FGuid CopiedSkeletonGuid=F.CopiedSkeleton->GetGuid();
        const FString CandidateDdcGuid=F.Candidate->GetImportedModel()->GetIdString();
        // Existing root scale amplifies a tiny local rotation into a formerly failing component-space ray.
        ChangePose(F.Candidate,FTransform(FQuat(FVector::UpVector,5.e-6),FVector(0,0,1.65)));
        const FString Before=UWarMageReviewLibrary::DescribeSkeletalReference(F.Candidate);
        auto& Lods=F.Candidate->GetImportedModel()->LODModels;
        Lods.Add(new FSkeletalMeshLODModel());
        Lods[0].IndexBuffer={0,1,2};Lods[0].RequiredBones={0,1,2};Lods[0].ActiveBoneIndices={0,1,2};
        Lods[0].Sections.AddDefaulted();
        FSoftSkinVertex V;FMemory::Memzero(V);
        V.Position=FVector3f(2,3,165);V.UVs[0]=FVector2f(.25f,.75f);
        V.InfluenceBones[0]=2;V.InfluenceWeights[0]=65535;
        Lods[0].Sections[0].SoftVertices={V,V,V};
        TestTrue(TEXT("Small proven round-trip discrepancy is restored"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(F.Candidate,F.Original,F.Root));
        for (int32 I=0;I<F.Original->GetRefSkeleton().GetNum();++I)
        {
            TestTrue(TEXT("Candidate reference is exact original transform"),F.Candidate->GetRefSkeleton().GetRefBonePose()[I].Equals(F.Original->GetRefSkeleton().GetRefBonePose()[I],0.0));
            TestTrue(TEXT("Candidate stored inverse is exact original"),F.Candidate->GetRefBasesInvMatrix()[I]==F.Original->GetRefBasesInvMatrix()[I]);
            TestTrue(TEXT("Candidate composed cache follows exact source"),F.Candidate->GetComposedRefPoseMatrix(I).Equals(F.Original->GetComposedRefPoseMatrix(I),0.0));
        }
        TestTrue(TEXT("Candidate index buffer unchanged"),Lods[0].IndexBuffer==TArray<uint32>{0,1,2});
        TestTrue(TEXT("Candidate required bones unchanged"),Lods[0].RequiredBones==TArray<FBoneIndexType>{0,1,2});
        TestTrue(TEXT("Candidate active bones unchanged"),Lods[0].ActiveBoneIndices==TArray<FBoneIndexType>{0,1,2});
        TestEqual(TEXT("Candidate source vertices unchanged count"),Lods[0].Sections[0].SoftVertices.Num(),3);
        for (const FSoftSkinVertex& After:Lods[0].Sections[0].SoftVertices)
        {
            TestTrue(TEXT("Candidate position unchanged"),After.Position==V.Position);
            TestTrue(TEXT("Candidate UV unchanged"),After.UVs[0]==V.UVs[0]);
            TestEqual(TEXT("Candidate bone influence unchanged"),After.InfluenceBones[0],V.InfluenceBones[0]);
            TestEqual(TEXT("Candidate weight unchanged"),After.InfluenceWeights[0],V.InfluenceWeights[0]);
        }
        TestTrue(TEXT("Candidate DDC invalidated"),F.Candidate->GetImportedModel()->GetIdString()!=CandidateDdcGuid);
        TestTrue(TEXT("Original DDC identity unchanged"),F.Original->GetImportedModel()->GetIdString()==OriginalDdcGuid);
        TestEqual(TEXT("Original mesh reference unchanged"),UWarMageReviewLibrary::DescribeSkeletalReference(F.Original),OriginalBefore);
        TestEqual(TEXT("Source skeleton reference unchanged"),UWarMageReviewLibrary::DescribeSkeletonReference(F.OriginalSkeleton),SourceSkeletonBefore);
        TestEqual(TEXT("Copied skeleton reference unchanged"),UWarMageReviewLibrary::DescribeSkeletonReference(F.CopiedSkeleton),CopiedSkeletonBefore);
        TestTrue(TEXT("Original skeleton GUID unchanged"),F.OriginalSkeleton->GetGuid()==OriginalSkeletonGuid);
        TestTrue(TEXT("Copied skeleton GUID unchanged"),F.CopiedSkeleton->GetGuid()==CopiedSkeletonGuid);
        TestEqual(TEXT("Original mesh package dirty state preserved"),F.Original->GetOutermost()->IsDirty(),DirtyOriginal);
        TestEqual(TEXT("Original skeleton package dirty state preserved"),F.OriginalSkeleton->GetOutermost()->IsDirty(),DirtyOriginal);
        TestFalse(TEXT("Copied skeleton package remains clean"),F.CopiedSkeleton->GetOutermost()->IsDirty());
        TestTrue(TEXT("Candidate retains copied skeleton pointer"),F.Candidate->GetSkeleton()==F.CopiedSkeleton);
        TestFalse(TEXT("Transient fixture candidate remains unsaved and clean"),F.Candidate->GetOutermost()->IsDirty());
        TestTrue(TEXT("Reference actually changed"),UWarMageReviewLibrary::DescribeSkeletalReference(F.Candidate)!=Before);
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMageRestoreThreadAndFiniteTest,
    "AegisWar.Foundation.MageReferenceRestore.ThreadAndFinite",WarMageReferenceRestoreTests::Flags)
bool FWarMageRestoreThreadAndFiniteTest::RunTest(const FString& Parameters)
{
    using namespace WarMageReferenceRestoreTests;
    FFixture F;
    auto Future=Async(EAsyncExecution::Thread,[&F] {return UWarMageReferenceRestore::RestoreDiagnosticMeshReference(F.Candidate,F.Original,F.Root);});
    TestFalse(TEXT("Off-thread call rejected before object reads"),Future.Get());
    auto Inverse=F.Candidate->GetRefBasesInvMatrix();Inverse[2].M[0][0]=std::numeric_limits<float>::infinity();
    F.Candidate->SetRefBasesInvMatrix(Inverse);
    TestFalse(TEXT("Nonfinite inverse rejected"),UWarMageReferenceRestore::RestoreDiagnosticMeshReference(F.Candidate,F.Original,F.Root));
    TestFalse(TEXT("Rejection does not dirty candidate"),F.Candidate->GetOutermost()->IsDirty());
    return true;
}
#endif
