#include "WarMageReferenceRestore.h"
#include "Animation/Skeleton.h"
#include "Engine/SkeletalMesh.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"

namespace
{
constexpr double MaximumLocalProbeErrorCm = .001;
constexpr double MaximumInverseProbeErrorCm = .0001;

bool PrivateObject(const UObject* Object, const FString& Root)
{
    const FString Prefix(TEXT("/Game/Characters/MageFaceDiagnostic/"));
    if (!IsValid(Object) || !Root.StartsWith(Prefix)) return false;
    const FString Suffix = Root.RightChop(Prefix.Len());
    if (Suffix.IsEmpty() || Suffix.Len() > 96) return false;
    for (const TCHAR C : Suffix)
        if (!((C >= TEXT('a') && C <= TEXT('z')) ||
              (C >= TEXT('0') && C <= TEXT('9')) || C == TEXT('_'))) return false;
    return Object->GetOutermost()->GetName().StartsWith(Root + TEXT("/"));
}

bool ValidReference(const FReferenceSkeleton& Ref)
{
    const int32 Count = Ref.GetNum();
    // This importer has no virtual bones; accepting them would also require matching raw/full index tables.
    if (Count < 1 || Count > 4096 || Ref.GetRawBoneNum() != Count || Ref.GetRefBonePose().Num() != Count
        || Ref.GetRawRefBonePose().Num() != Count) return false;
    for (int32 I = 0; I < Count; ++I)
    {
        const int32 Parent = Ref.GetParentIndex(I);
        const FTransform& Pose = Ref.GetRefBonePose()[I];
        if (Parent < INDEX_NONE || Parent >= I || Pose.ContainsNaN() || !Pose.GetRotation().IsNormalized() ||
            Pose.GetScale3D().GetAbsMin() <= UE_SMALL_NUMBER || !Ref.GetRawRefBonePose()[I].Equals(Pose, 0.0)) return false;
    }
    return true;
}

bool MatchingNamesParents(const FReferenceSkeleton& A, const FReferenceSkeleton& B)
{
    if (!ValidReference(A) || !ValidReference(B) || A.GetNum() != B.GetNum()) return false;
    for (int32 I = 0; I < A.GetNum(); ++I)
        if (A.GetBoneName(I) != B.GetBoneName(I) || A.GetParentIndex(I) != B.GetParentIndex(I)) return false;
    return true;
}

bool IdenticalReferences(const FReferenceSkeleton& A, const FReferenceSkeleton& B)
{
    if (!MatchingNamesParents(A, B)) return false;
    for (int32 I = 0; I < A.GetNum(); ++I)
        if (!A.GetRefBonePose()[I].Equals(B.GetRefBonePose()[I], 0.0)) return false;
    return true;
}

template<typename AType, typename BType>
bool CloseMatrices(const AType& A, const BType& B, double Limit)
{
    if (A.ContainsNaN() || B.ContainsNaN()) return false;
    for (const FVector P : {FVector::ZeroVector, FVector(100,0,0), FVector(0,100,0), FVector(0,0,100)})
    {
        // Preserve the installed native readback convention, including the rig's existing scale.
        const auto Transform = [&P](const auto& M)
        {
            return FVector(P.X*M.M[0][0]+P.Y*M.M[1][0]+P.Z*M.M[2][0]+M.M[3][0],
                P.X*M.M[0][1]+P.Y*M.M[1][1]+P.Z*M.M[2][1]+M.M[3][1],
                P.X*M.M[0][2]+P.Y*M.M[1][2]+P.Z*M.M[2][2]+M.M[3][2]);
        };
        if (FVector::Distance(Transform(A), Transform(B)) > Limit) return false;
    }
    return true;
}

bool CompleteInverse(const USkeletalMesh* Mesh)
{
    const auto& Inverse = Mesh->GetRefBasesInvMatrix();
    if (Inverse.Num() != Mesh->GetRefSkeleton().GetNum()) return false;
    for (const auto& M : Inverse) if (M.ContainsNaN()) return false;
    return true;
}
}

bool UWarMageReferenceRestore::RestoreDiagnosticMeshReference(USkeletalMesh* Candidate,
    const USkeletalMesh* Original, const FString& CandidateRoot)
{
    if (!IsInGameThread() || !PrivateObject(Candidate, CandidateRoot) || !IsValid(Original) || Candidate == Original ||
        Original->GetOutermost()->GetName().StartsWith(TEXT("/Game/Characters/MageFaceDiagnostic/")) ||
        FPackageName::DoesPackageExist(Candidate->GetOutermost()->GetName())) return false;
    USkeleton* CopiedSkeleton = Candidate->GetSkeleton();
    const USkeleton* SourceSkeleton = Original->GetSkeleton();
    if (!PrivateObject(CopiedSkeleton, CandidateRoot) || !IsValid(SourceSkeleton) || CopiedSkeleton == SourceSkeleton ||
        !IdenticalReferences(SourceSkeleton->GetReferenceSkeleton(), CopiedSkeleton->GetReferenceSkeleton())) return false;

    const FReferenceSkeleton& Before = Candidate->GetRefSkeleton();
    const FReferenceSkeleton& Source = Original->GetRefSkeleton();
    if (!MatchingNamesParents(Source, Before) || !CompleteInverse(Original) || !CompleteInverse(Candidate) ||
        !Candidate->GetImportedModel()) return false;
    for (int32 I = 0; I < Source.GetNum(); ++I)
    {
        if (!CloseMatrices(Source.GetRefBonePose()[I].ToMatrixWithScale(),
                Before.GetRefBonePose()[I].ToMatrixWithScale(), MaximumLocalProbeErrorCm) ||
            !CloseMatrices(Original->GetRefBasesInvMatrix()[I], Candidate->GetRefBasesInvMatrix()[I], MaximumInverseProbeErrorCm)) return false;
    }

    // Read all checked values before mutation. No source/skeleton/track/vertex/index/weight edits or saves.
    const FReferenceSkeleton ExactReference = Source;
    const TArray<FMatrix44f> ExactInverse = Original->GetRefBasesInvMatrix();
    Candidate->Modify();
    Candidate->SetRefSkeleton(ExactReference);
    // SetRefSkeleton does not clear the private composed cache. The supported calculator rebuilds it only
    // if inverse count differs; clear temporarily, rebuild from exact poses, then retain original stored floats.
    Candidate->SetRefBasesInvMatrix(TArray<FMatrix44f>());
    Candidate->CalculateInvRefMatrices();
    Candidate->SetRefBasesInvMatrix(ExactInverse);
    // A subsequent candidate material PostEditChange/build must not reuse old derived data.
    Candidate->InvalidateDeriveDataCacheGUID();
    return IdenticalReferences(Candidate->GetRefSkeleton(), ExactReference) &&
        Candidate->GetRefBasesInvMatrix().Num() == ExactInverse.Num() &&
        Candidate->GetSkeleton() == CopiedSkeleton;
}
