#include "WarImportLibrary.h"
#include "Materials/MaterialExpressionVectorParameter.h"
#include "Internationalization/Text.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

FString UWarImportLibrary::DescribeVectorParameter(UMaterialExpressionVectorParameter* Expression)
{
    auto Json=MakeShared<FJsonObject>();Json->SetNumberField(TEXT("schemaVersion"),1);
    Json->SetBoolField(TEXT("readOnly"),true);Json->SetBoolField(TEXT("available"),false);
    Json->SetStringField(TEXT("profile"),TEXT("vector_parameter_identity_v1"));
    Json->SetStringField(TEXT("expression"),FString());Json->SetStringField(TEXT("expressionClass"),FString());
    auto Values=MakeShared<FJsonObject>();Json->SetObjectField(TEXT("values"),Values);
    if (IsInGameThread() && IsValid(Expression))
    {
        bool Complete=Expression->ExpressionGUID.IsValid();
        const auto String=[&Complete](const FString& V)->TSharedPtr<FJsonValue>
        {
            if (V.Len()>4096) { Complete=false;return MakeShared<FJsonValueNull>(); }
            return MakeShared<FJsonValueString>(V);
        };
        const auto Number=[&Complete](double V)->TSharedPtr<FJsonValue>
        {
            if (!FMath::IsFinite(V)) { Complete=false;return MakeShared<FJsonValueNull>(); }
            return MakeShared<FJsonValueNumber>(V);
        };
        const auto Text=[&String](const FText& V)
        {
            FString History;FTextStringHelper::WriteToBuffer(History,V);
            auto Row=MakeShared<FJsonObject>();Row->SetField(TEXT("display"),String(V.ToString()));
            Row->SetField(TEXT("history"),String(History));return Row;
        };
        Json->SetStringField(TEXT("expression"),Expression->GetPathName());
        Json->SetStringField(TEXT("expressionClass"),Expression->GetClass()->GetName());
        Values->SetField(TEXT("parameter_name"),String(Expression->ParameterName.ToString()));
        const FLinearColor C=Expression->DefaultValue;
        Values->SetArrayField(TEXT("default_value"),{Number(C.R),Number(C.G),Number(C.B),Number(C.A)});
        Values->SetField(TEXT("group"),String(Expression->Group.ToString()));
        Values->SetNumberField(TEXT("sort_priority"),Expression->SortPriority);
        Values->SetStringField(TEXT("expression_guid"),Expression->ExpressionGUID.ToString(EGuidFormats::Digits));
        Values->SetBoolField(TEXT("use_custom_primitive_data"),Expression->bUseCustomPrimitiveData);
        Values->SetNumberField(TEXT("primitive_data_index"),Expression->PrimitiveDataIndex);
        auto Channels=MakeShared<FJsonObject>();
        Channels->SetObjectField(TEXT("r"),Text(Expression->ChannelNames.R));
        Channels->SetObjectField(TEXT("g"),Text(Expression->ChannelNames.G));
        Channels->SetObjectField(TEXT("b"),Text(Expression->ChannelNames.B));
        Channels->SetObjectField(TEXT("a"),Text(Expression->ChannelNames.A));
        Values->SetObjectField(TEXT("channel_names"),Channels);Json->SetBoolField(TEXT("available"),Complete);
    }
    FString Result;FJsonSerializer::Serialize(Json,TJsonWriterFactory<>::Create(&Result));
    if (FTCHARToUTF8(*Result).Length()>65536)
    {
        Json->SetBoolField(TEXT("available"),false);Json->SetObjectField(TEXT("values"),MakeShared<FJsonObject>());
        Result.Empty();FJsonSerializer::Serialize(Json,TJsonWriterFactory<>::Create(&Result));
    }
    return Result;
}
